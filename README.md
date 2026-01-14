Requirements:
Python >= 3.12 (Can probably get away with previous versions.)
Libraries Required: Keyboard, Openvr, NumPy, pyautogui, tkinter

Please change the file path string to your New Vegas /Data/Config/ path.
It won't work if you don't.

Run this program before entering New Vegas
DISCLAIMER
This needs the 3rd party program VorpX to run as it renders the game in virtual reality.You also need to run my python program, FNVR_Tracker, to grab headset and controller poses.
VorpX Link: https://www.vorpx.com (VorpX costs ~$40)
FNVR_Tracker Link: https://www.github.com/iloveusername/Fallout-New-Virtual-Reality


What Does This Mod Do?
	﻿Fallout: New Virtual Reality brings virtual reality motion controls into Fallout: New Vegas. With vanilla VorpX and NV, your gun is strapped to your face and you shoot directly where you look. Using this mod, your weapon will follow your hand and shoot in the direction you're pointing it. You can also point your gun to select NPCs and containers, as well as pick up and move objects. You can also use gestures to open the Pip-Boy, ESC Menu, and numbers 1 through 8 as hotkeys. Movement is controller centric rather than HMD centric. Overall, it makes for a more engaging and entertaining New Vegas VR experience.


How Do I Install The Mod?
Install New Vegas Script Extender
https://www.nexusmods.com/newvegas/mods/67883?tab=files
Download file. Copy contents and drag into your /Fallout New Vegas/ folder.

Install JIP PP LN
https://www.nexusmods.com/newvegas/mods/88687?tab=files
Download file. Copy contents and drag into your /Fallout New Vegas/Data/ folder.

Install ShowOffNVSE
https://www.nexusmods.com/newvegas/mods/72541?tab=files
Download file. Copy contents and drag into your /Fallout New Vegas/Data/ folder.

Install Fallout: New Virtual Reality
https://www.nexusmods.com/newvegas/mods/91589?tab=files
Download file. Copy contents and drag into your /Fallout New Vegas/Data/ folder.

Install FNV 4GB Patcher
https://www.nexusmods.com/newvegas/mods/62552?tab=files
Download the latest available .EXE file.
Place it in your /Fallout New Vegas/ folder.
Run the program as an administrator.

Install VR Tracker from Github
https://github.com/iloveusername/Fallout-New-Virtual-Reality/releases
Download the latest available .EXE file. 
Place the program wherever convenient.

Adjust Data Files
Launch the game normally through Steam or with FalloutNVLauncher.exe.
The launcher should open, select DATA FILES.
Make sure FNVR.esp is checked. Click OK.
Click Exit.


How Do I Use The Software?
Getting Ready To Play
You’ll have to go through some steps before playing. Please read the manual to understand how to play properly.
Ensure Steam VR is on.
Open the Fallout - New Virtual Reality.exe file. 

Setting the game directory
In the top left corner, click on the Set Game Directory button.
In the pop-up menu, navigate to the /Fallout New Vegas/ folder and click Select Folder.
The text above the Set Game Directory button should now read as your game directory.

Configuring controllers and beginning tracking
Press Start Tracking, underneath the Status & Hardware Info section.
Your primary controller acts as your weapon hand.
Your Secondary Controller acts as your hotkey hand.
For your Primary Controller, select Cycle Primary.
Move your desired controller around. Do your position and rotation readings underneath the Primary Controller section move?
For your Secondary Controller, select Cycle Secondary.
Move your desired controller around. Do your position and rotation readings underneath the Secondary Controller section move?
Once both controllers are properly set, move on.

Setting Hotkeys with Gestures
Hotkey positioning is calculated relative to your headset’s position and orientation. Meaning your activation spots move as you move your head.
Hotkeys are activated with your Secondary Controller.
The positions and orientations for these hotkeys are set by the user using the Set Current buttons under the Gesture Configuration section.
I recommend doing this next part in Steam VR’s desktop view mode, so that you can click the Set Current button with your other hand while holding a desired position.
Stand how you normally would while playing in VR. Hold your Secondary Controller in your desired position and click Set Current for your desired hotkey.
When you bring your secondary controller to this position and orientation again, it’ll trigger the hotkey.

Configuring sensitivities
If you find it too difficult or too easy to activate the hotkeys, you can modify either the Positional or Rotational Sensitivity to your liking.

Launching VorpX
Find the Start VorpX icon in the Start Menu.
Or find it under Animation Labs/vorpX/vorpControl.exe.

Launching NVSE
Under your /Fallout New Vegas/ folder, there should be an executable named nvse_loader.exe. With SteamVR, VorpX, and the FNVR Tracker all running, open this executable.
VorpX should now hook into the game and you should be in New Vegas VR.

Configuring VorpX
While in game, open the VorpX menu by pressing both grips down at once.
You can change your submenu using the top bar and your left joystick to traverse.
In the Head Tracking submenu, navigate to the HT Positional Tracking setting and disable it. This causes a lot of issues when left on.
In the Motion Controls submenu, I like to change my Controller Visualization setting to Overlay. 
In the Image Settings submenu, you can adjust the gamma if the game is too dark or too bright.
In the Main Settings submenu, make sure the 3D Reconstruction setting is set to Geometry.
If you notice anything feels off, you should recenter both with Steam and in the Main Settings submenu with Center Tracking.
Navigate to the bottom of the menu and click OK and SAVE.

Enabling Proper 3D
There’s a solid chance that something looks off with your game. When you load up VorpX for the first time with New Vegas, there’s still something you’ll have to do. 
When you get out of the bed in Doc Mitchell’s house, you need to open your VorpX menu with both grips.
In the Main submenu, click on full scan towards the bottom, then let it perform its process. Click OK and SAVE.
Open your escape menu and save your game, before exiting the game.
Reload your game with nvse_loader.exe and from now on, the 3D effect should be right.

Weapon Offsets
You can hold down the X key, which VorpX may actually map to a button on your controller in game, to set an anchor point and then drag to contribute to your offset. This lets you adjust where your weapon naturally sits in relation to your controller.
You can double tap the X key to reset your offsets.
One effective way to line things up is to hold your controller out in front of you how you’d feel most comfortable, then while in that position hold down whatever button corresponds to the X key. Then drag your controller around to affect the offset, you’ll see your weapon move. Move it where you’d want your weapon to sit where you previously had your hands. Release X when satisfied with your new values.


Required Mods:
	NVSEx,
	JP PP LN,
	ShowOFFNVSE,
	4GB Patch


Recommended Mods:
	Enhanced Bullet Impacts: It can be difficult in New Vegas VR to tell where your shots are ending up. Dramatic bullet impacts help you determine where you’re aiming. https://www.nexusmods.com/newvegas/mods/61804

	Any Bullet Time Mod: VATS is a no-go with my mod, so bullet time is the alternative. Plus, it makes you feel cool.

	Blur Killer: The blur effect from getting shot in New Vegas sucks in VR. Get rid of it!
https://www.nexusmods.com/newvegas/mods/41790


Usage:
	Use this code and mod as you see fit, but please keep it open source and give credit, too.

