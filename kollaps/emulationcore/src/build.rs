fn main() {
    capnpc::CompilerCommand::new()
        .file("src/messages.capnp")
        .run().expect("capnp compile failed");
}

