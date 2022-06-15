### Rust Files used in Kollaps 2.0
emulationcore is the emulationcore executable file \
libcommunicationcore.so is the communication core module used only by the dashboard \
communicationmanager is the communicatiormanager executable file.


#### Emulationcore
Install dependencies mentioned on https://github.com/foniod/redbpf \
To create the emulationcore executable run inside the emulationcore folder: \
```
cargo build --release
```
And then move the created module by running:
```
cp emulationcore/target/release/emulationcore ../rustbinaries/emulationcore

```

#### Communication Manager

To create the communicationmanager executable run inside the communicationmanager folder: 
```
cargo build --release
```
And then move the created module by running:
```
cp communicationmanager/target/release/communicationmanager ../rustbinaries/communicationamanager

```

#### Communication Core
Install dependencies mentioned on https://github.com/foniod/redbpf \
To create the libcommunicationcore.so module run inside the communicationcore folder: 
```
cd redbpf
cargo build --release
cd ..
cargo build --release
```

And then move the created module by running:

```
cp communicationcore/target/release/libcommunicationcore.so ../rustbinaries/libcommunicationcore.so
```
