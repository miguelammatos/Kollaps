## Monitor
This is the code that runs in the socket filter and increments the map every 25 miliseconds.

To compile this file you must have cargo bpf install via [Redbpf](https://github.com/foniod/redbpf).

Then do the following steps inside this folder:

```
cargo bpf build
```

```
cp target/bpf/programs/usage/usage.elf ../src/.
```