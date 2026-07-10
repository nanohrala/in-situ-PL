#In-Situ PL Code
import seabreeze
import matplotlib.pyplot as plt

seabreeze.use('cseabreeze')
from seabreeze.spectrometers import list_devices, Spectrometer

spec = Spectrometer.from_first_available()
spec.integration_time_micros(100000)

plt.plot(spec.wavelengths(), spec.intensities())
plt.show()
