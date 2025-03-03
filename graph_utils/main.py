#!/usr/bin/env python
import argparse
import gzip
import os
import shutil

import requests
from rdflib import Graph


class ZenodoRecord:
    """Handles fetching metadata from a Zenodo record."""

    def __init__(self, record_id: str, out_dir: str = "./data"):
        self.record_id = record_id
        self.out_dir = out_dir
        self.record_url = f"https://zenodo.org/api/records/{record_id}"
        self.metadata = None

    def fetch_metadata(self) -> None:
        """Fetches the JSON metadata for the given record."""
        response = requests.get(self.record_url, timeout=10)
        response.raise_for_status()
        self.metadata = response.json()

    def get_files(self) -> list:
        """Returns the list of file objects from the metadata."""
        if self.metadata is None:
            self.fetch_metadata()
        return self.metadata.get("files", [])


class FileDownloader:
    """Downloads files given a URL."""

    @staticmethod
    def download_file(url: str, dest_path: str) -> None:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)


class TTLConverter:
    """Converts Turtle files to N-Triples using rdflib."""

    @staticmethod
    def convert_ttl_to_nt(ttl_path: str, nt_path: str) -> None:
        g = Graph()
        g.parse(ttl_path, format="turtle")
        g.serialize(destination=nt_path, format="nt")


def decompress_gz(gz_path: str, dest_path: str) -> None:
    """Decompresses a .gz file to the specified destination."""
    with gzip.open(gz_path, "rb") as f_in, open(dest_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a Zenodo record, download .ttl.gz files, decompress them, and convert from TTL to NT."
    )
    parser.add_argument("record_id", help="Zenodo record ID (e.g., 10284416)")
    parser.add_argument("--out-dir", default="./data", help="Directory where files will be stored")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Fetch metadata for the Zenodo record
    record = ZenodoRecord(record_id=args.record_id, out_dir=args.out_dir)
    record.fetch_metadata()
    files = record.get_files()

    for file_info in files:
        # Each file info has a 'key' (file name) and download links.
        file_name = file_info.get("key")
        download_url = file_info.get("links", {}).get("self")
        if file_name and download_url and file_name.endswith(".ttl.gz"):
            gz_path = os.path.join(args.out_dir, file_name)
            ttl_file = file_name[:-3]  # Remove the .gz suffix to get the .ttl file name
            ttl_path = os.path.join(args.out_dir, ttl_file)
            nt_file = ttl_file.replace(".ttl", ".nt")
            nt_path = os.path.join(args.out_dir, nt_file)

            print(f"Downloading {file_name}...")
            FileDownloader.download_file(download_url, gz_path)

            print(f"Decompressing {gz_path} to {ttl_path}...")
            decompress_gz(gz_path, ttl_path)

            print(f"Converting {ttl_path} to {nt_path}...")
            TTLConverter.convert_ttl_to_nt(ttl_path, nt_path)

            print(f"Finished processing {file_name}.\n")


if __name__ == "__main__":
    main()
