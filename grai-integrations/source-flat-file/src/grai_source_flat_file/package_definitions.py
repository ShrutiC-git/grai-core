from grai_schemas.generics import PackageConfig


class Config(PackageConfig):
    integration_name = "grai-source-flat-file"
    metadata_id = "grai_source_flat_file"


config = Config()
