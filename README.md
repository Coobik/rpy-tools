# rpy-tools
Tools related to the Ren'Py Visual Novel Engine https://github.com/renpy/renpy

## RPY indexer (rpy_indexer.py)
Collect labels from .rpy files and build jump menus for fast navigation.

You will need Python 3 (3.8+)

### usage:
```
python3 rpy_indexer.py [-h] -i INPUT [-o OUTPUT] [-m MAIN_LABEL] [-s LABEL_PAGE_SIZE] [-p FILE_NAME_PREFIX] [-v]
```

### options:
```
-h, --help
  show this help message and exit

-i INPUT, --input INPUT
  Input directory path

-o OUTPUT, --output OUTPUT
  [Optional] Output directory path. Default: current directory

-m MAIN_LABEL, --main_label MAIN_LABEL
  [Optional] Main label name. Default: main_index

-s LABEL_PAGE_SIZE, --label_page_size LABEL_PAGE_SIZE
  [Optional] Max labels per menu page. Default: 20

-p FILE_NAME_PREFIX, --file_name_prefix FILE_NAME_PREFIX
  [Optional] Index file names prefix. Default: index_

-v, --version
  Show version
```

### sample usage:
```
python3 rpy_indexer.py --input "/path/to/input_directory" --output "/path/to/output_directory" -s 20 --main_label "my_cool_mod" -p "my_"
```

--
