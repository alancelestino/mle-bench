#!/usr/bin/env python
"""
Helper script to prepare a competition with local data (no Kaggle download).

This is useful for custom competitions where data is already available locally.
"""

import argparse
import hashlib
import shutil
from pathlib import Path

from mlebench.data import create_prepared_dir, is_dataset_prepared
from mlebench.registry import registry
from mlebench.utils import get_logger

logger = get_logger(__name__)


def get_checksum(file_path: Path) -> str:
    """Calculate MD5 checksum of a file."""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def generate_checksums(competition) -> dict:
    """Generate checksums for prepared data."""
    checksums = {}
    
    # Check public directory
    if competition.public_dir.exists():
        checksums['public'] = {}
        for file_path in sorted(competition.public_dir.rglob('*')):
            if file_path.is_file() and not file_path.name.startswith('.'):
                rel_path = file_path.relative_to(competition.public_dir)
                logger.info(f"Computing checksum for public/{rel_path}...")
                checksums['public'][str(rel_path)] = get_checksum(file_path)
    
    # Check private directory
    if competition.private_dir.exists():
        checksums['private'] = {}
        for file_path in sorted(competition.private_dir.rglob('*')):
            if file_path.is_file() and not file_path.name.startswith('.'):
                rel_path = file_path.relative_to(competition.private_dir)
                logger.info(f"Computing checksum for private/{rel_path}...")
                checksums['private'][str(rel_path)] = get_checksum(file_path)
    
    return checksums


def prepare_local_competition(
    competition_id: str,
    data_dir: Path = None,
    force: bool = False,
    generate_checksums_flag: bool = True,
):
    """
    Prepare a competition that uses local data instead of downloading from Kaggle.
    
    Args:
        competition_id: ID of the competition to prepare
        data_dir: Optional custom data directory
        force: If True, re-prepare even if already prepared
        generate_checksums_flag: If True, generate checksums after preparation
    """
    if data_dir:
        local_registry = registry.set_data_dir(Path(data_dir))
    else:
        local_registry = registry
    
    competition = local_registry.get_competition(competition_id)
    
    logger.info(f"Preparing local competition: {competition.id}")
    logger.info(f"Raw directory: {competition.raw_dir}")
    logger.info(f"Public directory: {competition.public_dir}")
    logger.info(f"Private directory: {competition.private_dir}")
    
    # Check if already prepared
    if is_dataset_prepared(competition) and not force:
        logger.info(f"Competition {competition.id} is already prepared. Use --force to re-prepare.")
        return
    
    # Create directories
    competition.raw_dir.mkdir(exist_ok=True, parents=True)
    create_prepared_dir(competition)
    
    logger.info(f"Running prepare function from {competition.prepare_fn.__module__}...")
    
    try:
        # Run the prepare function
        competition.prepare_fn(
            raw=competition.raw_dir,
            public=competition.public_dir,
            private=competition.private_dir,
        )
        logger.info("Prepare function completed successfully!")
    except Exception as e:
        logger.error(f"Error running prepare function: {e}")
        raise
    
    # Copy description to public directory
    logger.info("Copying description to public directory...")
    with open(competition.public_dir / "description.md", "w") as f:
        f.write(competition.description)
    
    # Generate checksums if requested
    if generate_checksums_flag:
        logger.info("Generating checksums...")
        checksums = generate_checksums(competition)
        
        # Save checksums to YAML
        import yaml
        checksums_path = competition.public_dir.parent.parent.parent / "mlebench" / "competitions" / competition.id / "checksums.yaml"
        checksums_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(checksums_path, 'w') as f:
            yaml.dump(checksums, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Checksums saved to {checksums_path}")
    
    logger.info(f"Competition {competition.id} prepared successfully!")
    logger.info(f"Public data available at: {competition.public_dir}")
    logger.info(f"Private data available at: {competition.private_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare a competition with local data (no Kaggle download)"
    )
    parser.add_argument(
        "-c",
        "--competition-id",
        required=True,
        help="ID of the competition to prepare",
    )
    parser.add_argument(
        "--data-dir",
        help="Path to the directory where the data will be stored",
        default=registry.get_data_dir(),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-preparation even if already prepared",
    )
    parser.add_argument(
        "--no-checksums",
        action="store_true",
        help="Skip checksum generation",
    )
    
    args = parser.parse_args()
    
    prepare_local_competition(
        competition_id=args.competition_id,
        data_dir=Path(args.data_dir) if args.data_dir else None,
        force=args.force,
        generate_checksums_flag=not args.no_checksums,
    )

