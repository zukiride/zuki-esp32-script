import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

for i, net in enumerate(wlan.scan()):
    for j, wifi in enumerate(net):
        print(wifi)
