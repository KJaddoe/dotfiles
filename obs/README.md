# OBS

Webcam and mic setup for video calls, with recording and streaming as a secondary use. OBS
composes the camera, screen and filtered mic, and its virtual camera (plus a virtual audio
device) hands the result to the call app.

## Install

| OS      | How                                  | Installs                                                               |
|---------|--------------------------------------|------------------------------------------------------------------------|
| macOS   | `_system/roles/obs` (Ansible)        | OBS, BlackHole 2ch, background removal plugin                          |
| Ubuntu  | `_system/roles/obs` (Ansible)        | OBS from `ppa:obsproject/obs-studio`, `v4l2loopback-dkms`              |
| Windows | Manual, see [Windows](#windows)      | OBS, Camo Studio, VB-CABLE, background removal plugin                  |

Run only this role with `ansible-playbook _system/main.yml -K --tags obs`.

Not covered:

- **Camo** is not installed on macOS and has no Linux client. On macOS, Continuity Camera can use
  the iPhone instead where the iPhone and macOS versions support it.
- **Background removal on Ubuntu**: the plugin's Linux package targets Debian, not Ubuntu; the
  alternatives are a source build or the Flatpak, which only works with Flatpak OBS.
- **Virtual audio on Ubuntu**: no device is set up; a PipeWire virtual sink is the equivalent.

### Windows

```powershell
winget install -e --id OBSProject.OBSStudio
winget install -e --id ReincubateLtd.CamoStudio
```

1. **VB-CABLE** is not in winget: download it from <https://vb-audio.com/Cable/>, run the
   installer as administrator, and reboot.
2. **Background removal plugin**: download `obs-backgroundremoval-<version>-windows-x64.zip` from
   the plugin's GitHub releases and copy its `obs-backgroundremoval` folder into
   `C:\ProgramData\obs-studio\plugins\`, creating that folder if it is missing.

## Scenes

Build the scenes once on Windows, export them with **Scene Collection > Export** to
`obs/scenes.json`, and load that file on another machine with **Scene Collection > Import**.

Capture sources are OS-specific source types (a Windows video capture device is not a macOS
one), so on another OS they import broken and must be re-added, not re-pointed. Keep them in a
single `Devices` scene that the other scenes include as a nested scene, so each machine only
fixes that one scene:

| Scene           | Contents                                                       |
|-----------------|----------------------------------------------------------------|
| `Devices`       | Camera, mic and display capture; never shown on its own        |
| `Camera`        | Camera, cropped and colour-corrected                           |
| `Screen + cam`  | Display capture with the camera in a corner                    |
| `Screen`        | Display capture only                                           |
| `Away`          | A still image, with the mic muted                              |

Give each scene a hotkey under **Settings > Hotkeys**.

Export only the scene collection, never a profile: a profile's `service.json` holds the stream
key, and this repository is public.

## Mic filters

On the mic source, in this order: Noise Suppression (RNNoise), Noise Gate, Compressor, Limiter.

## Sending the result to the call app

The virtual camera carries video only. For the call app to receive the filtered mic:

1. **Settings > Audio > Advanced > Monitoring Device**: `CABLE Input` (Windows) or
   `BlackHole 2ch` (macOS).
2. Mic source, **Advanced Audio Properties**: Audio Monitoring to **Monitor and Output**.
3. In the call app, pick `OBS Virtual Camera` as the camera and `CABLE Output` or
   `BlackHole 2ch` as the microphone.
