from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtMultimedia import QSound
import matplotlib 													# ogólny import biblioteki
matplotlib.use('Qt5Agg') 											# definiujemy backend którego ma używać biblioteka. Wskazujemy, że używamy PyQt w wersji 5
from matplotlib.figure import Figure 								# import obiektu "figury" której użyjemy do rysowania wykresów
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg 	# a tu widget z PyQt, który będzie wyświetlał się na ekranie
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar # widget PyQt5, toolbar do obsługi canvy
from scipy.io import wavfile 										# moduł wavfile posłuży do wczytywania plików dźwiękowych
from scipy.fft import rfft, rfftfreq								# do liczenia transformaty fouriera - "prawostronnej"
import scipy.signal													# do filtrowania syngału
import numpy
import sounddevice as sd
import soundfile as sf
import os
from matplotlib.mlab import window_hanning, window_none
class OknoGlowne():
	fileName = None 		# tu zapiszemy nazwę pliku (ścieżkę do pliku)
	soundObject = None 		# tu zapiszemy obiekty, których użyjemy do odegrania plików
	pobrany = None			# tu będziemy przechowywać wczytany plik (lub nagrany plik?)
	channel1 = None			# tu zapiszemy zawartość pierwszego kanału z pliku
	channel2 = None			# niestety program obsługuje tylko mono dźwięki :(
	fragmentFlag = False	# flaga dla dataToChannels i plotWave - jeśli True, to zamiast całych danych bierzemy tylko fragment
	fragmentToUse = None
	recordedFlag = False	# dla prawidłowego działania metody wholeFile - różne sposoby zapisu fileName przy powrocie do pełnego pliku
	#fs = 44100 
	#sd.default.samplerate = fs
	#sd.default.channels = 2

	# Wczytywanie plików z dysku
	def selectFile(self):
		self.recordedFlag = False
		self.pobrany = QFileDialog.getOpenFileName(self.window, 
									 "Otwórz plik dźwiękowy...",
									 "/home", 
									"Pliki audio (*.wav)")
		#print(self.pobrany)
		if not self.pobrany[0]:
			# jeśli nie wczytamy pliku, przerywamy wykonanie funkcji
			return			
		self.fileName = self.pobrany[0]	
		self.soundObject = QSound(self.fileName)
		self.form.choosenName.setStyleSheet(
                """QLineEdit { background-color: white; color: green }""")
		self.form.choosenName.setText(f"Wybrano plik {self.pobrany[0]}.")
		self.dataToChannels()
	# Rysowanie wykresu fali dźwiękowej
	def plotWave(self):
		self.figureSpec.clear()
		head, tail = os.path.split(self.fileName)
		self.figureSpec.suptitle(f"Spektrogram dla pliku {tail}.")
		# Dzielimy figurę na 16 podobszarów i wykorzystujemy trzy poziomo w prawym dolnym rogu
		axW = self.figureSpec.add_subplot(4,4,(14,16))
		axW.plot(self.channel1, color = 'gold')
		axW.set_facecolor((0,0,0))
		
		n_ticks = 5
		max_time = len(self.channel1)/self.rate
		if self.fragmentFlag == True:
			fragmentLow = self.form.spinFragmentLow.value()
			x_ticks = [(len(self.channel1) * i / (n_ticks - 1)) for i in range(n_ticks)]
			x_ticklabels = [f'{(max_time * i / (n_ticks - 1)) + fragmentLow:.2f}s' for i in range(n_ticks)]
		else:
			x_ticks = [len(self.channel1) * i / (n_ticks - 1) for i in range(n_ticks)]
			x_ticklabels = [f'{max_time * i / (n_ticks - 1):.2f}s' for i in range(n_ticks)]

		axW.margins(x=0.0)
		axW.set_xticks(x_ticks)
		axW.set_xticklabels(x_ticklabels)
		axW.set_yticks([])
		axW.set_yticklabels([])
		axW.set_xlabel('time [s]')
		
		self.figureSpecCanvas.draw()
	# Rysowanie wykresu transformaty Fouriera
	def fourierTransform(self):
		N = len(self.data)
		yf = rfft(self.channel1)
		xf = rfftfreq(N, 1/ self.rate)
		'''yf_abs      = numpy.abs(yf) 
		indices     = yf_abs>1000   # filter out those value under 300
		yf_clean    = indices * yf # noise frequency will be set to 0'''
		# Dzielimy figurę na 16 podobszarów i wykorzystujemy trzy pionowo w lewym górnym rogu
		axF = self.figureSpec.add_subplot(4,4,(1,9))
		axF.set_facecolor((0,0,0))
		axF.margins(y=0.0)
		axF.xaxis.tick_top()
		axF.set_ylabel('frequency [Hz]')
		axF.plot(numpy.absolute(yf), xf,color = 'gold')

		self.figureSpecCanvas.draw()
	# Wybór rodzaju okna do spektrogramu
	def whichWindow(self):
		if self.form.radioButtonN.isChecked() == True:
			return window_none
		elif self.form.radioButtonH.isChecked() == True:
			return window_hanning
	# Rysowanie wykresu spektrogramu
	def analizeFile(self): 
		if not self.soundObject:
			return
		axS = self.figureSpec.add_subplot(4,4,(2,12))
		axS.set_facecolor((0,0,0))
		n_ticks = 5
		x_ticks = [len(self.channel1) * i / (n_ticks - 1) for i in range(n_ticks)]
		
		axS.set_xticks(x_ticks)
		axS.set_xticklabels([])
		axS.set_yticklabels([])
		
		win = self.whichWindow()
		axS.specgram(self.channel1, NFFT=512,  Fs=self.rate, cmap = 'inferno',window= win, detrend='linear') #była cmap gnuplot
		self.figureSpecCanvas.draw()
	# Pobiera ze spinboxa, jeśli checkbox jest zaznaczony, liczbę sekund, czyli ile ma trwać nagranie
	def seconds(self): 
		s = 5
		spins = self.form.spinBox.value()
		if self.form.checkBox.isChecked():
			s = spins
		return s
	# Zapisuje obiekt w postaci pliku wav o wskazanej (w kodzie) nazwie i przekazuje do odtwarzania
	def makeSoundObject(self,nameString, dataArr, rate): 
		sf.write(nameString, dataArr, rate)
		self.fileName = nameString
		self.soundObject = QSound(self.fileName)
	# Nagrywa audio z domyślnego mikrofonu
	def recordAudio(self, s=5, cn=1):
		self.recordedFlag = True
		s = self.seconds() # ile sekund dźwięku użytkownik chce nagrać, default = 5
		self.nagranie = sd.rec(frames=44100*s, samplerate=44100, channels=cn, dtype=numpy.float64)
		sd.wait() # wstrzymuje wykonywanie kodu do czasu zakończenia nagrywania
		self.makeSoundObject("temp.wav", self.nagranie, 44100)
		self.form.choosenName.setStyleSheet(
                """QLineEdit { background-color: white; color: green }""")
		self.form.choosenName.setText(f"Nagrano dźwięk długości {s}s i zapisano jako temp.wav.")
		self.dataToChannels()
	
	def playSound(self):
		if not self.fileName: # przerywamy jeżeli plik nie został zdefiniowany
			self.form.choosenName.setStyleSheet(
                """QLineEdit { background-color: white; color: red }""")
			self.form.choosenName.setText(f"Najpierw wybierz lub nagraj dźwięk.")
			return
		self.soundObject.play()

	def stopSound(self):
		if not self.soundObject:
			self.form.choosenName.setStyleSheet(
                """QLineEdit { background-color: white; color: red }""")
			self.form.choosenName.setText(f"Najpierw wybierz lub nagraj dźwięk.")
			return
		self.soundObject.stop()
	
	def wholeFile(self):
		self.fragmentFlag=False # tu nie chcemy, żeby dataToChannels brało tylko wycięty fragment dźwięku
		self.form.choosenName.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
		self.form.choosenName.setText(f"Używam całego pliku.")
		#Resetujemy co przekazujemy do odtwarzacza, bo jednak chcemy używać całego pliku, a nie tylko jego fragmentu
		if not self.recordedFlag:
			self.fileName = self.pobrany[0]
		else:
			self.fileName = "temp.wav"
		self.soundObject = QSound(self.fileName)
		self.dataToChannels()
	
	def fragment(self):
		#Sprawdzamy, czy został już wybrany/nagrany plik. Jeśli nie, przerywamy działanie i drukujemy komunikat
		if not self.soundObject:
			self.form.choosenName.setStyleSheet(
                """QLineEdit { background-color: white; color: red }""")
			self.form.choosenName.setText(f"Najpierw wybierz lub nagraj dźwięk.")
			return
		#Wczytujemy dane z pliku
		self.rate, self.data = wavfile.read(self.fileName)
		#Zczytujemy dane ze spinBoxów - początek i koniec fragmentu, który chcemy przeanalizować. Obsługujemy niechciane przypadki.
		fragmentLow = self.form.spinFragmentLow.value()
		fragmentHigh = self.form.spinFragmentHigh.value()
		soundLength = len(self.channel1)/self.rate
		if fragmentHigh > soundLength:
			self.form.choosenName.setStyleSheet("""QLineEdit { background-color: white; color: red }""")
			self.form.choosenName.setText(f"Wybrany fragment wykracza poza długość wczytanego dźwięku. Aby wybrać inny fragment niż poprzednio, najpierw naciśnij \"Użyj całego pliku\".")
			return
		elif fragmentLow > fragmentHigh:
			self.form.choosenName.setStyleSheet("""QLineEdit { background-color: white; color: red }""")
			self.form.choosenName.setText(f"Koniec fragmentu musi być późniejszy niż początek fragmentu.")
			return
		#Wykrawamy z danych kawałek wybrany przez użytkownika
		self.fragmentToUse = self.data[int(fragmentLow*self.rate):int(fragmentHigh*self.rate)]
		self.fragmentFlag = True 
		#print(fragmentLow,  fragmentHigh, self.fragmentToUse, len(self.data), len(self.channel1)/self.rate)
		self.form.choosenName.setStyleSheet("""QLineEdit { background-color: white; color: green }""")
		self.form.choosenName.setText(f"Wybrano fragment od {fragmentLow}s do {fragmentHigh}s. Cały plik ma długość {soundLength:.2f}s.")
		self.dataToChannels()
		self.makeSoundObject("fragmented.wav", self.data, self.rate)
		
	
	def dataToChannels(self):
		self.rate, self.data = wavfile.read(self.fileName)
		if self.fragmentFlag == True:
			self.data = self.fragmentToUse
		if len(self.data.shape) == 1: # mono
			self.channel1 = self.data[:]
			self.channel2 = None
		else: # stereo lub więcej
			self.channel1 = self.data[:,0]
			self.channel2 = self.data[:,1]
		#print(self.data)
		#self.fragment()
		self.plotWave()
		self.fourierTransform()
	
	# Niedokończone funkcjonalności filtrowania Low, High i Band Pass, działają, ale niepoprawnie
	def filterSignalL(self):
		#self.dataToChannels()
		b, a = scipy.signal.butter(4, 0.1, 'lowpass')
		filteredLowPass = scipy.signal.filtfilt(b, a, self.data, padlen = 0)
		
		if len(self.data.shape) == 1: # mono
			self.channel1 = filteredLowPass[:]
			self.channel2 = None
		else: # stereo lub więcej
			self.channel1 = filteredLowPass[:,0]
			self.channel2 = filteredLowPass[:,1]
		#self.makeSoundObject("filtered.wav", filteredLowPass, self.rate)
		self.plotWave()
		self.fourierTransform()
		self.analizeFile()
	
	def filterSignalH(self):
		#self.dataToChannels()
		#sos = scipy.signal.butter(10, 15, 'hp', fs=44100, output='sos')
		#filteredHighPass = scipy.signal.sosfilt(sos, self.data)
		b, a = scipy.signal.butter(4, 0.3, 'highpass')
		filteredHighPass = scipy.signal.filtfilt(b, a, self.data, padlen = 0)
		
		if len(self.data.shape) == 1: # mono
			self.channel1 = filteredHighPass[:]
			self.channel2 = None
		else: # stereo lub więcej
			self.channel1 = filteredHighPass[:,0]
			self.channel2 = filteredHighPass[:,1]
		#self.makeSoundObject("filtered.wav", filteredHighPass, self.rate)
		self.plotWave()
		self.fourierTransform()
		self.analizeFile()
		
	def filterSignalB(self):
		#self.dataToChannels()
		b, a = scipy.signal.butter(4, [.1, .6], 'band')
		filteredBandPass = scipy.signal.filtfilt(b, a, self.data, padlen = 0)
		
		if len(self.data.shape) == 1: # mono
			self.channel1 = filteredBandPass[:]
			self.channel2 = None
		else: # stereo lub więcej
			self.channel1 = filteredBandPass[:,0]
			self.channel2 = filteredBandPass[:,1]
		#self.makeSoundObject("filtered.wav", filteredBandPass, self.rate)
		self.plotWave()
		self.fourierTransform()
		self.analizeFile()

	def __init__(self):

		Form, Window = uic.loadUiType("spektrogramMainWindow.ui")
		self.app = QApplication([])
		self.app.setStyle('Fusion')
		self.window = Window()
		self.form = Form()
		self.form.setupUi(self.window)
		self.window.show()
		

		# odpowiednie zachowanie guzików
		self.form.chooseFile.clicked.connect(self.selectFile)
		self.form.recordSound.clicked.connect(self.recordAudio) 
		self.form.checkBox.stateChanged.connect(self.seconds)
		self.form.playButton.clicked.connect(self.playSound)
		self.form.pauseButton.clicked.connect(self.stopSound)
		self.form.useFragment.clicked.connect(self.fragment)
		self.form.useWhole.clicked.connect(self.wholeFile)
		# filtry
		self.form.lowPass.clicked.connect(self.filterSignalL)
		self.form.lowPass.setToolTip('Cyfrowy filtr low-pass Butterwortha') 
		self.form.highPass.clicked.connect(self.filterSignalH)
		self.form.highPass.setToolTip('Cyfrowy filtr high-pass Butterwortha') 
		self.form.bandPass.clicked.connect(self.filterSignalB)
		self.form.bandPass.setToolTip('Cyfrowy filtr band-pass Butterwortha') 
		# rysowanie spektrogramu i sound wave
		self.form.analyse.clicked.connect(self.analizeFile)
		self.form.analyse.setToolTip('Rysuje spektrogram dla wybranego lub nagranego pliku') 
		self.figureSpec = Figure()
		self.figureSpecCanvas = FigureCanvasQTAgg(self.figureSpec)
		self.figureSpec.set_facecolor("cornflowerblue")
		self.figureSpec.tight_layout()
		self.figureSpec.set_size_inches(6.4, 8.8, forward=True)
		#Toolbar umożliwia zapis obrazka, ma funkcję lupy
		self.toolbar = NavigationToolbar(self.figureSpecCanvas, parent=None)
		self.form.spectrogramPlaceholder.addWidget(self.toolbar)
		self.form.spectrogramPlaceholder.addWidget(self.figureSpecCanvas)
		
		self.app.exec()
		
if __name__ == "__main__":
	klasa = OknoGlowne() #to jest zmienna przechowująca obiekt klasy OknoGlowne, zawiera wszystkie zmienne i funkcje tam zdefiniowane
