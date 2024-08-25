from netifaces import interfaces, ifaddresses, AF_INET

HMI_SERVER = "https://192.168.30.10/"  # Partner to answer
BACKEND_IP = ""
BACKEND_PORT = 8443

#Find the own IP: BACKEND_IP

for ifaceName in interfaces():
    addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
    if addresses[0].startswith('192.168') :
        BACKEND_IP = addresses[0]
