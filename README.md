# habsvm-themachine
Simple SVM implementation for turning devices on/off based on Temperature. 

I'm using it with paired with OpenHAB + mqtt. The details below assume OpenHAB is already
configured and you have existing knowledge about how rules/items work.

Install + Running
=================
Eg Virtualenv

```
mkdir ~/themachine
cd ~/themachine
virtualenv -p /usr/bin/python3 venv
source venv/bin/activate
pip install -r requirements.txt
```

```
python themachine.py mqttserver ~/themachine/learn
```
NOTE: The path must exist and be writeable

If you want it to run on boot and you have a systemd based distro put this in
a file `/etc/systemd/system/themachine.service`

```
[Unit]
Description=The Machine - OpenHAB SVM Service
After=syslog.target network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/themachine
ExecStart=/home/username/themachine/venv/bin/python themachine.py hostname /home/username/themachine/learn
Restart=on-abort
```

```
sudo systemctl enable themachine.service
sudo systemctl start themachine.service
```


Training
========

Listens for learn events on '/themachine/learn' in the following format:
```
location,item,state,inTemp,inHumidity,outTemp,outHumidity
```

To trigger a learn event, I've configured a dummy switch which a rule listens to:
```
rule "shedfanManTrigger"
when
  Item shedfanManSwitch changed OFF to ON or
  Item shedfanManSwitch changed ON to OFF
then
  // Only publish events that are as a result of the manual switch trigger
  if ( shedfanManSwitch.state.toString != shedfanSwitch.state.toString ) {
    sendCommand(shedfanSwitch, shedfanManSwitch.state.toString)
    var message = "shed,shedFan," + shedfanManSwitch.state + "," + shedTemperature.state + "," + shedHumidity.state + "," + shedOutTemperature.state + "," + shedOutHumidity.state
    publish("hedwig","/themachine/learn",message)
  }
end
```

To keep the state of the dummy switch in sync, there is a separate rule to update the state of the switch
```
rule "shedfanTrigger"
when
  Item shedfanSwitch changed from OFF to ON or
  Item shedfanSwitch changed from ON to OFF
then
  sendCommand(shedfanManSwitch, shedfanSwitch.state.toString)
end
```

Changes
=======
Listens for learn events on '/themachine/change' in the following format:

```
location,inTemp,inHumidity,outTemp,outHumidity
```

And publishes back to '/themachine/location/item' eg Event

```
2016-12-29 15:42:35,710 INFO     Change: shed,26.40,46.80,30.20,39.60
2016-12-29 15:42:35,712 INFO     I'm 99.97% sure you wanted the shedFan off
```

Would publish 'OFF' to '/themachine/shed/shedFan'


