import argparse
import os
import shutil
from pathlib import Path


def list_files_recursive(path: Path, accepted_extensions: set[str]) -> list[Path]:
    file_paths = []
    for root, _, files in os.walk(path):
        for file in files:
            if "." + file.split('.')[-1] in accepted_extensions:
                file_paths.append(Path(os.path.join(root, file)))

    return file_paths


def copy_books(book_list: list[Path], output_folder_path: Path, dry_run: bool):
    for book in book_list:
        output_path = output_folder_path / book.name
        if not output_path.exists():
            if not dry_run:
                shutil.copyfile(book, output_path)
            else:
                print(f"Dry run: {book} would be copied to {output_path}")


def main(input_folder_path: Path, output_folder_path: Path, dry_run: bool = False):
    book_paths =list_files_recursive(input_folder_path, {".pdf", ".epub", ".mobi"})  # Add more extensions as needed
    copy_books(book_list=book_paths, output_folder_path=output_folder_path, dry_run=dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check media in a folder")
    parser.add_argument("input_folder_path", type=str, help="The path of the source book folder")
    parser.add_argument("output_folder_path", type=str, help="The path of the output folder")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without copying files")
    args = parser.parse_args()
    input_folder_path = Path(args.input_folder_path)
    output_folder_path = Path(args.output_folder_path)
    main(input_folder_path=input_folder_path, output_folder_path=output_folder_path, dry_run=args.dry_run)