from labd._visa import VisaProxy

visa = VisaProxy()
rm = visa.ResourceManager()
print(rm.list_resources())
inst = rm.open_resource('GPIB0::21::INSTR')
print(inst.write('FREQ 150'))
