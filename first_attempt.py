#In-Situ PL Code
import seabreeze
import matplotlib.pyplot as plt

seabreeze.use('pyseabreeze')
import seabreeze.cseabreeze as csb
from seabreeze.spectrometers import list_devices, Spectrometer

print(list_devices())

#spec = Spectrometer.from_first_available()
#spec.integration_time_micros(100000)

#plt.plot(spec.wavelengths(), spec.intensities())
#plt.show()
