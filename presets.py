import uuid

from metadata import MetadataStore


def add_default_presets(user_id: uuid.UUID, ms: MetadataStore):
    """Add the default presets to the metadata store"""
    # # make sure humans/personas added
    # add_default_humans_and_personas(user_id=user_id, ms=ms)

    # # add default presets
    # for preset_name in preset_options:
    #     if ms.get_preset(user_id=user_id, name=preset_name) is not None:
    #         continue

    #     preset = load_preset(preset_name, user_id)
    #     ms.create_preset(preset)
    pass
