# OBS

Webcam and mic setup for video calls, with recording and streaming as a secondary use. OBS
composes the camera, screen and filtered mic, and its virtual camera (plus a virtual audio
device) hands the result to the call app.

## Install

| OS      | How                                            | Installs                                                          |
|---------|------------------------------------------------|-------------------------------------------------------------------|
| macOS   | `_system/roles/obs` (Ansible)                  | OBS, BlackHole 2ch, background removal plugin, config             |
| Ubuntu  | `_system/roles/obs` (Ansible)                  | OBS from `ppa:obsproject/obs-studio`, `v4l2loopback-dkms`, config |
| Windows | `obs/install.ps1`, from an elevated PowerShell | OBS, Camo Studio, PowerShell 7, background removal plugin, config |

Run only the role with `ansible-playbook _system/main.yml -K --tags obs`. On Windows, install
VB-CABLE first: it is not in winget, so download it from <https://vb-audio.com/Cable/>, run its
installer as administrator and reboot. Then run `obs\install.ps1` as administrator. It makes
Administrators the owner of `C:\ProgramData\obs-studio\plugins` and leaves other users read
access only, because by default any user can add a plugin there that OBS would load.

Every step is safe to re-run; one that has nothing to do prints `ok`.

## Generated config

`configure.ps1` writes OBS's config; the role and `install.ps1` run it. It refuses to run while OBS
is open, because OBS writes its config when it exits and would undo the change.

The repo owns this config: a setting changed only in the OBS UI is put back on the next run.
Change it in `configure.ps1` instead, and experiment in a separate profile or scene collection,
which the script never touches. It also never touches `service.json`, which holds the stream key.

What it writes, in OBS's config directory:

| File                                | Contents                                                 |
|-------------------------------------|----------------------------------------------------------|
| `basic/profiles/dotfiles/basic.ini` | 1920x1080 canvas and the monitoring device               |
| `basic/scenes/dotfiles.json`        | Sources, scenes and the mic                              |
| `user.ini`                          | Only the `[Basic]` keys that make OBS open the two above |

Scenes: `Camera`, `Screen + cam` (camera bottom right), `Screen` and `Away` (a dark background).
The mic is the system default input, set to Monitor and Output, with Noise Suppression (RNNoise),
Noise Gate, Compressor and Limiter in that order.

Devices are looked up on each machine at run time:

| OS      | Camera                                                | Screen                  | Monitoring device |
|---------|-------------------------------------------------------|-------------------------|-------------------|
| macOS   | The built-in camera                                   | The main display        | BlackHole 2ch     |
| Windows | The camera already chosen in any OBS scene collection | Same rule as the camera | CABLE Input       |
| Ubuntu  | The first `/dev/video*`                               | None                    | None              |

On a Windows machine where OBS has never had the camera or screen chosen, pick them once in the
`Webcam` and `Display` sources, then re-run `configure.ps1`: it keeps what you picked. Ubuntu has
no screen scenes, because PipeWire screen capture asks for permission on every start, and no
monitoring device yet.

## Using it in a call

1. Start the virtual camera in OBS (**Start Virtual Camera**). On macOS, the first start asks you
   to allow OBS's camera extension in System Settings.
2. In the call app, pick `OBS Virtual Camera` as the camera and `BlackHole 2ch` (macOS) or
   `CABLE Output` (Windows) as the microphone. The virtual camera carries video only; the
   filtered mic reaches the call through that virtual audio device.

## Tests

`configure.Tests.ps1` covers the generator with Pester, which the `powershell` role installs.
`script/test-powershell.ps1` runs it together with PSScriptAnalyzer, as CI does:

```sh
./script/test-powershell.ps1
```
