# RPY generator 1.0.1
# Copyright (C) 2023 by Coobik, https://github.com/Coobik
# All rights reserved.
# This file is part of rpy-tools, https://github.com/Coobik/rpy-tools
# and is released under the GNU General Public License v3.0
# https://github.com/Coobik/rpy-tools/blob/main/LICENSE

from argparse import ArgumentParser
import io
import os
import sys
from io import TextIOWrapper
import time
from typing import Any, Dict, Generator, List, Mapping, NamedTuple, Optional, Tuple
import yaml


VERSION = "1.0.1"
URL = "https://github.com/Coobik/rpy-tools"

MODE_READ = "r"
MODE_WRITE = "w"
ENCODING_UTF_8 = "utf-8"

LABEL = "label"
LABEL_START_POS = len(LABEL)
MAIN_LABEL = "main"

EXT_TXT = ".txt"
EXT_TXT_LENGTH = len(EXT_TXT)

EXT_RPY = ".rpy"
EXT_RPY_LENGTH = len(EXT_RPY)

TAB = "    "
COLON = ":"
ELLIPSIS = "..."

MAX_LABELS_PER_MENU = 20


def current_time_millis() -> int:
    return round(time.time() * 1000)


class ScriptLine(NamedTuple):
    character_name: Optional[str]
    phrase: str


class ScriptConfig:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.config = self.load_yaml_config(file_path=file_path)

    def load_yaml_config(self, file_path: str) -> Mapping[str, Any]:
        with io.open(
            file=file_path,
            mode=MODE_READ,
            encoding=ENCODING_UTF_8,
        ) as config_file:
            return yaml.safe_load(config_file)

    @property
    def characters(self) -> Dict[str, str]:
        return self.config.get("characters") or {}


def normalize_label(
    label: Optional[str] = None,
    default_label: Optional[str] = None,
) -> str:
    if label:
        label = label.strip()

    if not label:
        if default_label:
            return default_label

        return f"{LABEL}_{str(current_time_millis())}"

    label = label.replace(" ", "_")
    label = label.replace(COLON, "_")

    if label[0].isdigit():
        return f"{LABEL}_{label}"

    return label


def parse_text_line(line: str) -> Optional[ScriptLine]:
    if not line:
        return None

    line = line.strip()

    if not line:
        return None

    colon_index = line.find(COLON)

    if colon_index < 1:
        # character name not defined in screenplay line
        line = line.lstrip(COLON)

        if line:
            return ScriptLine(character_name=None, phrase=line)

        return None

    line_length = len(line)
    character_name = line[0:colon_index].rstrip()

    if colon_index == (line_length - 1):
        return ScriptLine(
            character_name=(character_name if character_name else None),
            phrase=ELLIPSIS,
        )

    phrase = line[(colon_index + 1) :].strip()

    if (not character_name) and (not phrase):
        return None

    return ScriptLine(
        character_name=(character_name if character_name else None),
        phrase=(phrase if phrase else ELLIPSIS),
    )


def read_lines_from_file(file_path: str) -> Generator[ScriptLine, Any, None]:
    print("source:", file_path)

    with io.open(
        file=file_path,
        mode=MODE_READ,
        encoding=ENCODING_UTF_8,
    ) as screenplay_file:
        while True:
            line = screenplay_file.readline()

            if not line:
                break

            script_line = parse_text_line(line)

            if script_line is not None:
                yield script_line


def write_lines_to_script_file(
    script_file: TextIOWrapper,
    lines_generator: Generator[ScriptLine, Any, None],
    character_map: Dict[str, str],
) -> int:
    lines_count = 0

    if not lines_generator:
        return lines_count

    for line in lines_generator:
        if line is None:
            continue

        if line.character_name:
            character_id = character_map.setdefault(
                line.character_name,
                f"ch_{len(character_map)}",
            )
        else:
            character_id = None

        script_line = (
            f'{character_id} "{line.phrase}"' if character_id else f'"{line.phrase}"'
        )

        script_file.write(f"{TAB}{script_line}\n")
        lines_count += 1

    return lines_count


def prepare_output_file_path_and_chapter_label(
    output_dir_path: str,
    file_name: str,
) -> Tuple[str, str]:
    """
    :returns: output_file_path, chapter_label
    """

    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)

    output_file_path = os.path.join(output_dir_path, file_name)

    chapter_label = file_name[:-EXT_RPY_LENGTH]
    chapter_label = normalize_label(label=chapter_label)

    if os.path.exists(output_file_path):
        file_name = f"{chapter_label}_{str(current_time_millis())}{EXT_RPY}"
        output_file_path = os.path.join(output_dir_path, file_name)

    return output_file_path, chapter_label


def write_script_file(
    output_dir_path: str,
    file_name: str,
    lines_generator: Generator[ScriptLine, Any, None],
    character_map: Dict[str, str],
) -> Tuple[str, int]:
    """
    :returns: chapter_label, lines_count
    """

    output_file_path, chapter_label = prepare_output_file_path_and_chapter_label(
        output_dir_path=output_dir_path,
        file_name=file_name,
    )

    with io.open(
        file=output_file_path,
        mode=MODE_WRITE,
        encoding=ENCODING_UTF_8,
    ) as script_file:
        script_file.write(f"{LABEL} {chapter_label}:\n\n")

        lines_count = write_lines_to_script_file(
            script_file=script_file,
            lines_generator=lines_generator,
            character_map=character_map,
        )

        if not lines_count:
            script_file.write(f"{TAB}pass\n")

    print("target:", output_file_path, "chapter:", chapter_label, "lines:", lines_count)
    return chapter_label, lines_count


def generate_script_file_name(source_file_name: str) -> str:
    if not source_file_name:
        return f"script{EXT_RPY}"

    source_file_name = source_file_name.strip(".")

    if not source_file_name:
        return f"script{EXT_RPY}"

    last_dot_index = source_file_name.rfind(".")

    if last_dot_index < 0:
        return f"{source_file_name}{EXT_RPY}"

    return f"{source_file_name[0:last_dot_index]}{EXT_RPY}"


def process_text_file(
    dir_path: str,
    file_name: str,
    output_dir_path: str,
    character_map: Dict[str, str],
) -> Tuple[str, int]:
    """
    :returns: chapter_label, lines_count
    """

    source_file_path = os.path.join(dir_path, file_name)
    script_file_name = generate_script_file_name(source_file_name=file_name)
    lines_generator = read_lines_from_file(source_file_path)

    chapter_label, lines_count = write_script_file(
        output_dir_path=output_dir_path,
        file_name=script_file_name,
        lines_generator=lines_generator,
        character_map=character_map,
    )

    return chapter_label, lines_count


def process_text_files(
    input_dir_path: str,
    output_dir_path: str,
    ext: Optional[str] = None,
    config: Optional[ScriptConfig] = None,
) -> Tuple[List[str], Dict[str, str]]:
    """
    :returns: chapter_labels, character_map
    """

    chapter_labels = []
    character_map = config.characters if config else {}
    total_lines = 0

    if not input_dir_path:
        return chapter_labels, character_map

    for dir_path, dir_names, file_names in os.walk(input_dir_path):
        for file_name in file_names:
            if ext and (not file_name.endswith(ext)):
                continue

            try:
                chapter_label, lines_count = process_text_file(
                    dir_path=dir_path,
                    file_name=file_name,
                    output_dir_path=output_dir_path,
                    character_map=character_map,
                )

                total_lines += lines_count

                if chapter_label:
                    chapter_labels.append(chapter_label)

            except Exception as ex:
                print(
                    "Error processing file:",
                    os.path.join(dir_path, file_name),
                    str(ex),
                )

                continue

    print(f"\nProcessed {len(chapter_labels)} {ext or ''} files")
    print(f"Found {len(character_map)} characters")
    print(f"Total script lines: {total_lines}")
    return chapter_labels, character_map


def write_jump_menu_to_script_file(
    script_file: TextIOWrapper,
    top_label: str,
    labels: List[str],
    go_back_label: Optional[str] = None,
):
    script_file.write(f"{LABEL} {top_label}:\n\n")

    if (not go_back_label) and (not labels):
        script_file.write(f"{TAB}pass\n")
        return

    script_file.write(f"{TAB}menu:\n")

    if go_back_label:
        script_file.write(f'{TAB}{TAB}"< BACK":\n')
        script_file.write(f"{TAB}{TAB}{TAB}jump {go_back_label}\n\n")

    if not labels:
        return

    for label in labels:
        script_file.write(f'{TAB}{TAB}"{label}":\n')
        script_file.write(f"{TAB}{TAB}{TAB}jump {label}\n\n")


def batch_labels(labels: List[str], batch_size: int) -> Generator[list[str], Any, None]:
    if (not batch_size) or (batch_size < 1):
        return

    if not labels:
        return

    labels_count = len(labels)

    for i in range(0, labels_count, batch_size):
        yield labels[i : min(i + batch_size, labels_count)]


def write_labels_to_script_file(
    script_file: TextIOWrapper,
    labels: List[str],
    root_label: str,
    label_page_size: int = MAX_LABELS_PER_MENU,
):
    if (not label_page_size) or (label_page_size < 1):
        label_page_size = MAX_LABELS_PER_MENU

    if (not labels) or (len(labels) <= label_page_size):
        write_jump_menu_to_script_file(
            script_file=script_file,
            top_label=root_label,
            labels=labels,
        )

        return

    batch_number = 0
    batch_top_labels = []

    # write submenus
    for labels_batch in batch_labels(labels=labels, batch_size=label_page_size):
        top_label = f"{root_label}_{batch_number}"
        batch_top_labels.append(top_label)

        write_jump_menu_to_script_file(
            script_file=script_file,
            top_label=top_label,
            labels=labels_batch,
            go_back_label=root_label,
        )

        batch_number += 1

    # write top menu
    write_jump_menu_to_script_file(
        script_file=script_file,
        top_label=root_label,
        labels=batch_top_labels,
    )


def write_init_to_script_file(
    script_file: TextIOWrapper,
    character_map: Dict[str, str],
    mod_id: Optional[str] = None,
):
    script_file.write("init:\n")

    if (not character_map) and (not mod_id):
        script_file.write(f"{TAB}pass\n")
        return

    if mod_id:
        script_file.write(f'{TAB}$ mods["{mod_id}"] = u"{mod_id}"\n')

    if character_map:
        for character_name, character_id in character_map.items():
            script_file.write(
                f'{TAB}define {character_id} = Character(u"{character_name}")\n'
            )

    script_file.write("\n")


def create_main_rpy_file(
    chapter_labels: List[str],
    character_map: Dict[str, str],
    output_dir_path: str,
    main_label: str,
    label_page_size: int = MAX_LABELS_PER_MENU,
):
    if not chapter_labels:
        return

    output_file_name = main_label + EXT_RPY
    print("Writing main script file:", main_label)

    output_file_path, _ = prepare_output_file_path_and_chapter_label(
        output_dir_path=output_dir_path,
        file_name=output_file_name,
    )

    print("target:", output_file_path, "labels:", len(chapter_labels))

    with io.open(
        file=output_file_path,
        mode=MODE_WRITE,
        encoding=ENCODING_UTF_8,
    ) as main_file:
        write_init_to_script_file(
            script_file=main_file,
            character_map=character_map,
            mod_id=main_label,
        )

        write_labels_to_script_file(
            script_file=main_file,
            labels=chapter_labels,
            root_label=main_label,
            label_page_size=label_page_size,
        )


def generate_rpy_files(
    input_dir_path: str,
    output_dir_path: Optional[str] = None,
    main_label: Optional[str] = None,
    label_page_size: int = MAX_LABELS_PER_MENU,
    config_file_path: Optional[str] = None,
):
    if input_dir_path:
        input_dir_path = input_dir_path.strip()

    if not input_dir_path:
        print("Input directory path is not defined")
        return

    if output_dir_path:
        output_dir_path = output_dir_path.strip()

    if not output_dir_path:
        output_dir_path = os.getcwd()
        print("Output directory path is not defined - using current:", output_dir_path)

    main_label = normalize_label(label=main_label, default_label=MAIN_LABEL)

    config = ScriptConfig(config_file_path) if config_file_path else None

    chapter_labels, character_map = process_text_files(
        input_dir_path=input_dir_path,
        output_dir_path=output_dir_path,
        ext=EXT_TXT,
        config=config,
    )

    create_main_rpy_file(
        chapter_labels=chapter_labels,
        character_map=character_map,
        output_dir_path=output_dir_path,
        main_label=main_label,
        label_page_size=label_page_size,
    )


def build_argument_parser() -> ArgumentParser:
    argument_parser = ArgumentParser(
        prog="python3 rpy_generator.py",
        description="Read plain text screenplay files and generate .rpy script files",
        epilog=URL,
    )

    argument_parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Input directory path",
    )

    argument_parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="[Optional] Output directory path. Default: current directory",
    )

    argument_parser.add_argument(
        "-m",
        "--main_label",
        default=MAIN_LABEL,
        type=str,
        required=False,
        help=f"[Optional] Main label name. Default: {MAIN_LABEL}",
    )

    argument_parser.add_argument(
        "-s",
        "--label_page_size",
        default=MAX_LABELS_PER_MENU,
        type=int,
        required=False,
        help=f"[Optional] Max labels per menu page. Default: {MAX_LABELS_PER_MENU}",
    )

    argument_parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=False,
        help="[Optional] YAML config file path",
    )

    argument_parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="Show version",
        version=f"RPY generator {VERSION}",
    )

    return argument_parser


def main() -> int:
    print("\nRPY generator")
    print(f"{URL}\n")

    argument_parser = build_argument_parser()
    args = argument_parser.parse_args()

    try:
        generate_rpy_files(
            input_dir_path=args.input,
            output_dir_path=args.output,
            main_label=args.main_label,
            label_page_size=args.label_page_size,
            config_file_path=args.config,
        )

    except Exception as ex:
        print("Error generating RPY files:", str(ex))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
