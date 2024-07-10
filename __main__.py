import argparse
import json

from typing import List, Tuple, Set
from pathlib import Path
from git import Repo, Commit
from prompt_toolkit.shortcuts import checkboxlist_dialog
from shutil import copy2


class EnvFile:
    output_path: str
    ignore: List[str]

    def __init__(self):
        file: Path = Path(".").joinpath("env.json")
        with open(file, 'r') as config_file:
            file_json: dict = json.load(config_file)
            self.output_path = file_json["output-path"] 
            self.ignore = file_json["ignore"]


env_file: EnvFile = EnvFile()


def copy_files(files: Set[str], directory: str, git_root: Path) -> None:
    git_root_dir: Path = git_root.parent 
    copy_root_dir: Path = Path(env_file.output_path).joinpath(directory)
    if not copy_root_dir.exists():
        copy_root_dir.mkdir()

    # Gets the parent folder name from .git directory
    copy_dir: Path = copy_root_dir.joinpath(git_root.parent.stem)
    print(str(copy_dir))
    for file in files:
        local_file_path: Path = git_root_dir.joinpath(file) 
        copy_file_path: Path = copy_dir.joinpath(file)

        if not local_file_path.exists():
            raise Exception(f"File not found: {file}")

        if not copy_file_path.exists():
            copy_file_path.parent.mkdir(parents=True, exist_ok=True)

        copy2(local_file_path.absolute(), copy_file_path.absolute())
        

def is_ignored_file(path: Path) -> bool:
    global env_file

    for pattern in env_file.ignore:
        print(path)
        if path.match(pattern):
            return True
    return False


def files_from_commits(commits: List[Tuple[str, Commit]], repository_path: Path) -> Set[str]:
    files: Set[str] = set() 

    for msg, commit in commits:
        for file in commit.stats.files:
            file_path = repository_path.joinpath(file)
            if not is_ignored_file(file_path):
                files.add(str(file))

    return files


def show_prompt(commits: List[Tuple[str, Commit]]) -> List[Tuple[str, Commit]]: 
    dialog_data = []
    for commit in commits:
        dialog_data.append((commit[1].hexsha, commit[0].strip()))

    results = checkboxlist_dialog(
        title="Commit list",
        text="Select the commits",
        values=dialog_data
    ).run()

    if len(results) == 0:
        return []

    selected_commits: List[Tuple[str, Commit]] = []
    for commit in commits:
        if not commit[1].hexsha in results:
            continue

        selected_commits.append(commit)

    return selected_commits


def get_commits(max: int, repository: Repo) -> List[Tuple[str, Commit]]: 
    commits: List[Tuple[str, Commit]] = []
    commit_iter = repository.iter_commits(all=True, max_count=max)
    for commit in commit_iter:
        commits.append((str(commit.message), commit))
    return commits


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="Commit File Extractor"
    )

    parser.add_argument(
        "project", 
        nargs=1,
        help="The path where it is located the '.git' folder"
    )

    parser.add_argument(
        "outputdir",
        nargs=1,
        help="The path where the files will be extracted"
    )

    parser.add_argument(
        "--max-commits",
        "-m",
        nargs=1,
        default=10,
        help="Define the max number of commits to display"
    )

    args = parser.parse_args()

    path: Path = Path(args.project[0])
    if not path.exists():
        raise RuntimeError(
            f"The path {str(path)} does not exists"
        ) 

    repository: Repo = Repo(path.absolute())
    commits = get_commits(args.max_commits, repository)
    selected_commits = show_prompt(commits)
    files_paths = files_from_commits(selected_commits, path) 
    copy_files(files_paths, args.outputdir[0], Path(repository.git_dir))