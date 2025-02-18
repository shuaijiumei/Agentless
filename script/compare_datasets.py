#!/usr/bin/env python3
import datasets
from typing import Set, Dict, Any
import json
from pathlib import Path
import pandas as pd
from tabulate import tabulate

def load_dataset(dataset_name: str) -> datasets.Dataset:
    """Load dataset from Hugging Face."""
    return datasets.load_dataset(dataset_name, split="test")

def get_unique_items(dataset1: datasets.Dataset, dataset2: datasets.Dataset, 
                    key_field: str = "instance_id") -> tuple[Set[str], Set[str]]:
    """
    Find unique items in each dataset based on a key field.
    Returns two sets: (unique_in_dataset1, unique_in_dataset2)
    """
    keys1 = set(str(item[key_field]) for item in dataset1)
    keys2 = set(str(item[key_field]) for item in dataset2)
    
    unique_in_1 = keys1 - keys2
    unique_in_2 = keys2 - keys1
    
    return unique_in_1, unique_in_2

def extract_item_info(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant information from a dataset item."""
    return {
        'ID': str(item['instance_id']),
        'Problem': item['problem_statement'][:100] + '...' if len(item['problem_statement']) > 100 else item['problem_statement'],
        'Repository': item.get('repo', 'N/A')
    }

def create_unique_items_df(dataset: datasets.Dataset, unique_keys: Set[str], key_field: str = "instance_id") -> pd.DataFrame:
    """Create a DataFrame with unique items."""
    unique_items = [extract_item_info(item) for item in dataset if str(item[key_field]) in unique_keys]
    return pd.DataFrame(unique_items)

def save_unique_items(dataset: datasets.Dataset, unique_keys: Set[str], 
                     output_file: str, key_field: str = "instance_id"):
    """Save unique items to a JSON file."""
    unique_items = [item for item in dataset if str(item[key_field]) in unique_keys]
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_items, f, indent=2, ensure_ascii=False)

def display_table(df: pd.DataFrame, title: str):
    """Display a beautiful table with the given title."""
    print(f"\n{title}")
    print("=" * len(title))
    print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
    print(f"Total entries: {len(df)}\n")

def main():
    # Load datasets
    print("Loading swe-bench-lite dataset...")
    swe_bench = load_dataset("princeton-nlp/SWE-bench_Lite")
    
    print("Loading swt-bench-lite dataset...")
    swt_bench = load_dataset("nmuendler/SWT-bench_Lite_bm25_27k_zsb")
    
    # Find unique items
    unique_in_swe, unique_in_swt = get_unique_items(swe_bench, swt_bench)
    
    # Create DataFrames for unique items
    swe_unique_df = create_unique_items_df(swe_bench, unique_in_swe)
    swt_unique_df = create_unique_items_df(swt_bench, unique_in_swt)
    
    # Display tables
    display_table(swe_unique_df, "Unique Items in SWE-bench-lite")
    display_table(swt_unique_df, "Unique Items in SWT-bench-lite")
    
    # Save results
    save_unique_items(swe_bench, unique_in_swe, "output/unique_in_swe_bench.json")
    save_unique_items(swt_bench, unique_in_swt, "output/unique_in_swt_bench.json")
    
    print("Detailed results have been saved to:")
    print("- output/unique_in_swe_bench.json")
    print("- output/unique_in_swt_bench.json")

if __name__ == "__main__":
    main() 