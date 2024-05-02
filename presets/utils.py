import glob
import yaml
import os

from constants import MEMGPT_DIR


def load_yaml_file(file_path):
    """
    Load a YAML file and return the data.

    :param file_path: Path to the YAML file.
    :return: Data from the YAML file.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_all_presets():
    """Load all the preset configs in the examples directory"""

    ## Load the examples
    # Get the directory in which the script is located
    script_directory = os.path.dirname(os.path.abspath(__file__))
    # Construct the path pattern
    example_path_pattern = os.path.join(script_directory, "examples", "*.yaml")
    # Listing all YAML files
    example_yaml_files = glob.glob(example_path_pattern)

    ## Load the user-provided presets
    # ~/.memgpt/presets/*.yaml
    user_presets_dir = os.path.join(MEMGPT_DIR, "presets")
    # Create directory if it doesn't exist
    if not os.path.exists(user_presets_dir):
        os.makedirs(user_presets_dir)
    # Construct the path pattern
    user_path_pattern = os.path.join(user_presets_dir, "*.yaml")
    # Listing all YAML files
    user_yaml_files = glob.glob(user_path_pattern)

    # Pull from both examplesa and user-provided
    all_yaml_files = example_yaml_files + user_yaml_files

    # Loading and creating a mapping from file name to YAML data
    all_yaml_data = {}
    for file_path in all_yaml_files:
        # Extracting the base file name without the '.yaml' extension
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        data = load_yaml_file(file_path)
        all_yaml_data[base_name] = data

    return all_yaml_data
