fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto_file = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("proto/voile.proto");
    tonic_build::compile_protos(proto_file)?;
    Ok(())
}
