from labd._ok import OKProxy

serial = '1839000NJV'

ok = OKProxy(('localhost', 4292))
devices = ok.okCFrontPanelDevices()
print(devices.GetCount())

xem = devices.Open()
#xem = devices.Open(serial)
print(xem.GetSerialNumber())
xem.Close()
