# RPY generator 1.0.4 (ES edition)
# Copyright (C) 2023 - 2026 by Coobik, https://github.com/Coobik
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


VERSION = "1.0.4 (ES edition)"
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

PLAY_MUSIC = "music>"
PLAY_AMBIENCE = "ambience>"
PLAY_SOUND_LOOP = "sound_loop>"
PLAY_SOUND = "sound>"

ASSET_DIRECTIVES_MAP = {
    PLAY_MUSIC: "play music music_list['{asset_id}'] fadein 3",
    PLAY_AMBIENCE: "play ambience {asset_id} fadein 2",
    PLAY_SOUND_LOOP: "play sound_loop {asset_id} fadein 1",
    PLAY_SOUND: "play sound {asset_id}",
}

CH_SHOW = "show>"
CH_HIDE = "hide>"

CH_DIRECTIVES_MAP = {
    CH_SHOW: "show {character_id} normal pioneer at center with dissolve",
    CH_HIDE: "hide {character_id} with dissolve",
}


def current_time_millis() -> int:
    return round(time.time() * 1000)


class ScriptLine(NamedTuple):
    character_name: Optional[str]
    phrase: str
    is_raw: bool = False


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

    @property
    def assets(self) -> Dict[str, str]:
        return self.config.get("assets") or {}


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


def normalize_character_name(character_name: str) -> Optional[str]:
    if not character_name:
        return None

    character_name = character_name.strip()

    if not character_name:
        return None

    character_name = character_name.replace("ё", "е")
    character_name = character_name.replace("Ё", "Е")

    character_name = character_name.title()

    return character_name


def get_character_id(character_name: str, character_map: Dict[str, str]) -> Optional[str]:
    if not character_name:
        return None

    normalized_name = normalize_character_name(character_name) or character_name

    return (
        character_map.get(character_name)
        or character_map.get(normalized_name)
        or character_map.setdefault(normalized_name, f"ch_{len(character_map)}")
    )


def build_ch_directive_line(
    line: str,
    character_map: Dict[str, str],
    ch_directive: str,
) -> Optional[ScriptLine]:
    if not line.startswith(ch_directive):
        return None

    raw_name = line[len(ch_directive):].strip()

    if not raw_name:
        return None

    ch_directive_format = CH_DIRECTIVES_MAP.get(ch_directive)

    if not ch_directive_format:
        return None

    character_id = get_character_id(character_name=raw_name, character_map=character_map)

    if not character_id:
        return None

    phrase = ch_directive_format.format(character_id=character_id)
    return ScriptLine(character_name=None, phrase=phrase, is_raw=True)


def build_scene_directive_line(line: str, asset_map: Dict[str, str]) -> Optional[ScriptLine]:
    if not line:
        return None

    if not (line.startswith("INT ") or line.startswith("EXT ")):
        return None

    location = line[4:].strip()
    time_of_day = "day"
    
    hyphen_index = location.rfind("-")

    if hyphen_index > 0:
        suffix = location[hyphen_index + 1:].strip().lower()

        if suffix in ("day", "eve", "night"):
            time_of_day = suffix
            location = location[:hyphen_index].strip()

    scene_id = asset_map.get(location)

    if not scene_id:
        scene_id = location.lower().replace(" ", "_")

    if time_of_day == "day":
        phrase = (
            "stop sound_loop fadeout 1\n"
            "stop music fadeout 3\n"
            "stop ambience fadeout 2\n"
            '$ persistent.sprite_time = "day"\n'
            f"scene bg {scene_id}\n"
            "with dissolve\n"
            "$ day_time()"
        )

        return ScriptLine(character_name=None, phrase=phrase, is_raw=True)

    if time_of_day == "eve":
        phrase = (
            "stop sound_loop fadeout 1\n"
            "stop music fadeout 3\n"
            "stop ambience fadeout 2\n"
            '$ persistent.sprite_time = "sunset"\n'
            f"scene bg {scene_id}\n"
            "with dissolve2\n"
            "$ sunset_time()"
        )

        return ScriptLine(character_name=None, phrase=phrase, is_raw=True)

    if time_of_day == "night":
        phrase = (
            "stop sound_loop fadeout 1\n"
            "stop music fadeout 3\n"
            "stop ambience fadeout 2\n"
            '$ persistent.sprite_time = "night"\n'
            f"scene bg {scene_id}\n"
            "with dissolve2\n"
            "$ night_time()"
        )

        return ScriptLine(character_name=None, phrase=phrase, is_raw=True)

    return None


def build_asset_directive_line(line: str) -> Optional[ScriptLine]:
    if not line:
        return None

    for directive_tag, asset_directive in ASSET_DIRECTIVES_MAP.items():
        if not line.startswith(directive_tag):
            continue

        asset_id = line[len(directive_tag):].strip()

        if not asset_id:
            return None

        return ScriptLine(
            character_name=None,
            phrase=asset_directive.format(asset_id=asset_id),
            is_raw=True,
        )

    return None


def parse_text_line(
    line: str,
    asset_map: Dict[str, str],
    character_map: Dict[str, str],
) -> Optional[ScriptLine]:
    if not line:
        return None

    line = line.strip()

    if not line:
        return None

    if line.startswith("#"):
        return ScriptLine(character_name=None, phrase=line, is_raw=True)

    ch_show_line = build_ch_directive_line(line=line, character_map=character_map, ch_directive=CH_SHOW)

    if ch_show_line:
        return ch_show_line

    ch_hide_line = build_ch_directive_line(line=line, character_map=character_map, ch_directive=CH_HIDE)

    if ch_hide_line:
        return ch_hide_line

    scene_directive_line = build_scene_directive_line(line, asset_map)

    if scene_directive_line:
        return scene_directive_line

    asset_directive_line = build_asset_directive_line(line)

    if asset_directive_line:
        return asset_directive_line

    colon_index = line.find(COLON)

    if colon_index < 1:
        # character name not defined in screenplay line
        line = line.lstrip(COLON)

        if line:
            return ScriptLine(character_name=None, phrase=line)

        return None

    line_length = len(line)
    character_name = line[0:colon_index]
    character_name = normalize_character_name(character_name)

    if colon_index == (line_length - 1):
        return ScriptLine(
            character_name=character_name,
            phrase=ELLIPSIS,
        )

    phrase = line[(colon_index + 1) :].strip()
    phrase = phrase.replace('"', '\\"')

    if (not character_name) and (not phrase):
        return None

    return ScriptLine(
        character_name=character_name,
        phrase=(phrase if phrase else ELLIPSIS),
    )


def read_lines_from_file(
    file_path: str,
    asset_map: Dict[str, str],
    character_map: Dict[str, str],
) -> Generator[ScriptLine, Any, None]:
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

            script_line = parse_text_line(line=line, asset_map=asset_map, character_map=character_map)

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

        if line.is_raw:
            for raw_line in line.phrase.splitlines():
                script_file.write(f"{TAB}{raw_line}\n")

            lines_count += 1
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
    asset_map: Dict[str, str],
) -> Tuple[str, int]:
    """
    :returns: chapter_label, lines_count
    """

    source_file_path = os.path.join(dir_path, file_name)
    script_file_name = generate_script_file_name(source_file_name=file_name)
    lines_generator = read_lines_from_file(file_path=source_file_path, asset_map=asset_map, character_map=character_map)

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
    character_map = dict(config.characters) if config else {}
    asset_map = dict(config.assets) if config else {}
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
                    asset_map=asset_map,
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
    print(f"Found {len(asset_map)} assets mapping")
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
