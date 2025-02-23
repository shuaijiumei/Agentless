#!/usr/bin/env python3
import ast
import os
import argparse
from typing import List, Tuple, Dict, Any, Literal
from pathlib import Path
import json
import subprocess
import datasets
from logging import Logger
ElementType = Literal['class', 'function', 'variable']

class TestFinder(ast.NodeVisitor):
    def __init__(self, target_name: str, element_type: ElementType):
        self.target_name = target_name
        self.element_type = element_type
        self.test_functions: List[Tuple[ast.FunctionDef, bool]] = []
        self.current_function = None
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions and track if they use the target element."""
        old_function = self.current_function
        self.current_function = node
        self.generic_visit(node)
        
        # Check if this is a test function (starts with 'test_' or in a Test class)
        is_test = node.name.startswith('test_') or (
            isinstance(node.parent, ast.ClassDef) and 
            node.parent.name.startswith('Test')
        )
        
        # If it's a test and we found the target usage, add it
        if is_test and any(usage for usage in self.test_functions if usage[0] == node):
            self.test_functions.append((node, True))
            
        self.current_function = old_function
        
    def visit_Name(self, node: ast.Name):
        """Visit name nodes to find usage of the target element."""
        if self.current_function and node.id == self.target_name:
            # For variables, we need to check if it's being used as a variable
            if self.element_type == 'variable':
                if isinstance(node.ctx, ast.Load):  # Variable being used
                    if self.current_function not in [func for func, _ in self.test_functions]:
                        self.test_functions.append((self.current_function, False))
            # For functions, check if it's being called
            elif self.element_type == 'function':
                if isinstance(node.parent, ast.Call) and node.parent.func == node:
                    if self.current_function not in [func for func, _ in self.test_functions]:
                        self.test_functions.append((self.current_function, False))
            # For classes, check if it's being used in type context
            elif self.element_type == 'class':
                if self.current_function not in [func for func, _ in self.test_functions]:
                    self.test_functions.append((self.current_function, False))
        self.generic_visit(node)

def find_test_files(repo_root: str) -> List[str]:
    """Find all Python test files in the repository."""
    test_files = []
    for root, _, files in os.walk(repo_root):
        for file in files:
            if file.endswith('.py') and ('test' in file.lower() or 'test' in root.lower()):
                test_files.append(os.path.join(root, file))
    return test_files

def analyze_test_file(file_path: str, target_name: str, element_type: ElementType) -> List[Tuple[str, int, int, str]]:
    """
    Analyze a test file for usage of the target element.
    Returns list of (file_path, start_line, end_line, code) tuples.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        # Set parent references for all nodes
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node
                
        finder = TestFinder(target_name, element_type)
        finder.visit(tree)
        
        results = []
        for func, is_test in finder.test_functions:
            if is_test:
                # Get the source code lines
                start_line = func.lineno
                end_line = func.end_lineno
                code_lines = content.splitlines()[start_line-1:end_line]
                code = '\n'.join(code_lines)
                
                results.append((file_path, start_line, end_line, code))
        
        return results
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return []

# TODO: 请在 Agentless/playground_manual/repositories 下面 clone 好需要的仓库
def get_repo_path(repo_name: str) -> str:
    """Get the full path to the repository."""
    # repo_name 只取 / 后半部分
    repo_name = repo_name.split("/")[-1]
    base_path = Path("/mnt/d/vscodeProject/Agentless/playground_manual/repositories")
    repo_path = base_path / repo_name
    if not repo_path.exists():
        raise ValueError(f"Repository '{repo_name}' not found in {base_path}")
    return str(repo_path)

def find_tests(target_name: str, source_file: str, repo_path: str, element_type: ElementType) -> List[Tuple[str, int, int, str]]:
    """
    Find all test functions that use the specified element.
    Returns list of (file_path, start_line, end_line, code) tuples.
    """
    # Convert source_file to be relative to repo root if it's absolute
    if os.path.isabs(source_file):
        try:
            source_file = os.path.relpath(source_file, repo_path)
        except ValueError:
            raise ValueError(f"Source file '{source_file}' must be within repository")
    
    # Find all test files
    test_files = find_test_files(repo_path)
    
    # Analyze each test file
    all_results = []
    for test_file in test_files:
        results = analyze_test_file(test_file, target_name, element_type)
        all_results.extend(results)
    
    return all_results

def get_dataset_item(instance_id: str) -> Dict[str, Any]:
    """Load item from SWE-bench-lite dataset by instance_id."""
    print("Loading SWE-bench-lite dataset...")
    dataset = datasets.load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    
    for item in dataset:
        if item['instance_id'] == instance_id:
            return item
    
    raise ValueError(f"Instance ID '{instance_id}' not found in the dataset")

def parse_element_info(item: str) -> Tuple[str, ElementType]:
    """Parse element information from a string."""
    if item.startswith("class: "):
        return item.split(": ")[1], 'class'
    elif item.startswith("function: "):
        return item.split(": ")[1], 'function'
    elif item.startswith("variable: "):
        return item.split(": ")[1], 'variable'
    else:
        raise ValueError(f"Unknown element type in item: {item}")

def find_element_tests(instance_id: str, found_related_locs, cache_dir: str, logger: Logger) -> Dict[str, List[Dict[str, Any]]]:
    """
    Main function to find test code for elements (classes, functions, variables).
    Args:
        instance_id: Instance ID from the dataset
        json_file: Path to the JSON file containing element information
    Returns:
        Dictionary with element names as keys and list of test information as values.
        Each test info contains: {
            'file_path': str,
            'start_line': int,
            'end_line': int,
            'code': str,
            'source_file': str,
            'element_type': str
        }
    """
    # Load element information from JSON file
    element_info_list = []
    for file_path, items in found_related_locs.items():
        processed_items = []
        for item in items:
            if "\n" in item:
                processed_items.extend(item.split("\n"))
            else:
                processed_items.append(item)
        
        for item in processed_items:
            try:
                element_name, element_type = parse_element_info(item)
                element_info_list.append({
                    "name": element_name,
                    "type": element_type,
                    "source_file": file_path
                })
            except ValueError:
                continue  # Skip items that don't match expected format
    
    if not element_info_list:
        raise ValueError("JSON file must contain valid element information")
    # Create cache file if it doesn't exist
    cache_data = {}
    if os.path.exists(cache_dir):
        try:
            with open(cache_dir, "r") as f:
                cache_data = json.load(f)
        except json.JSONDecodeError:
            # If cache file is corrupted, start with empty cache
            cache_data = {}
        
    # Check cache for each element
    for element_info in element_info_list:
        cache_key = f"{instance_id}_{element_info['source_file']}_{element_info['type']}_{element_info['name']}"
        if cache_key in cache_data:
            element_info['tests'] = cache_data[cache_key]
    # Get dataset item
    dataset_item = get_dataset_item(instance_id)
    repo_name = dataset_item['repo']
    base_commit = dataset_item['base_commit']
    
    # Get repository path and checkout base commit
    repo_path = get_repo_path(repo_name)
    logger.info(f"\nChecking out base commit {base_commit} in repository {repo_name}...")
    subprocess.run(["git", "checkout", base_commit], cwd=repo_path, check=True, capture_output=True)
    
    try:
        # Find test code
        results_list = []
        for element_info in element_info_list:
            if 'tests' in element_info:
                results_list.append({
                    'element_name': element_info['name'],
                    'element_type': element_info['type'],
                    'source_file': element_info['source_file'],
                    'tests': element_info['tests']
                })
                continue

            element_name = element_info["name"]
            element_type = element_info["type"]
            results_list.append({
                'element_name': element_name,
                'element_type': element_type,
                'source_file': element_info["source_file"],
                'tests': []
            })

            results = find_tests(element_name, element_info["source_file"], repo_path, element_type)
            
            if results:
                tests = []
                for file_path, start_line, end_line, code in results:
                    tests.append({
                        'file_path': file_path,
                        'start_line': start_line,
                        'end_line': end_line,
                        'code': code,
                    })
                    cache_key = f"{instance_id}_{element_info['source_file']}_{element_info['type']}_{element_info['name']}"
                    cache_data[cache_key] = tests
                
                    # Write updated cache to file
                    os.makedirs(os.path.dirname(cache_dir), exist_ok=True)
                    with open(cache_dir, "w") as f:
                        json.dump(cache_data, f, indent=2)
                results_list[-1]['tests'] = tests
                   
        return results_list
    finally:
        # Try to checkout main branch, if fails try master
        logger.info("\nRestoring to main branch...")
        try:
            subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            try:
                print("Main branch not found, trying master...")
                subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print("Warning: Could not restore to main/master branch")

def print_test_results(results_list: List[Dict[str, Any]], _: str = None):
    """
    Print test results in a formatted way.
    Args:
        results_list: List of dictionaries containing test information
        _: Unused parameter (kept for backward compatibility)
    """
    if not results_list:
        print("\nNo test code found.")
        return

    # Calculate statistics
    total_elements = len(results_list)
    total_tests = sum(len(result['tests']) for result in results_list)
    test_files = set()
    for result in results_list:
        for test in result['tests']:
            if test['file_path']:  # Only count non-empty file paths
                test_files.add(test['file_path'])
    total_files = len(test_files)
    
    print("\nTest Code Analysis Results")
    print("=" * 80)
    
    # Group results by element type
    results_by_type = {}
    for result in results_list:
        element_type = result['element_type']
        if element_type not in results_by_type:
            results_by_type[element_type] = []
        results_by_type[element_type].append(result)
    
    # Print results grouped by type
    for element_type, elements in sorted(results_by_type.items()):
        print(f"\n{element_type.upper()} ({len(elements)} found)")
        print("=" * 40)
        
        for element in elements:
            element_name = element['element_name']
            source_file = element['source_file']
            print(f"\n{element_type.capitalize()}: {element_name}")
            print(f"Defined in: {source_file}")
            print("-" * 40)
            
            # Group tests by file
            tests_by_file = {}
            for test in element['tests']:
                if test['file_path']:  # Skip empty test entries
                    tests_by_file.setdefault(test['file_path'], []).append(test)
            
            if not tests_by_file:
                print("\nNo test code found for this element.")
                continue
            
            # Print tests for each file
            for file_path, file_tests in tests_by_file.items():
                rel_path = os.path.relpath(file_path, os.path.dirname(source_file))
                print(f"\nTest file: {rel_path}")
                print(f"Found {len(file_tests)} test functions:")
                
                for test_idx, test in enumerate(sorted(file_tests, key=lambda x: x['start_line']), 1):
                    print(f"\n  {test_idx}. Lines {test['start_line']}-{test['end_line']}:")
                    # Indent the code with proper spacing
                    code_lines = test['code'].splitlines()
                    if code_lines:
                        # Print first line with less indentation (usually the function definition)
                        print(f"     {code_lines[0]}")
                        # Print remaining lines with more indentation
                        for line in code_lines[1:]:
                            print(f"       {line}")
    
    # Print summary
    print("\nSUMMARY")
    print("=" * 40)
    print(f"Total elements found: {total_elements}")
    for element_type, elements in sorted(results_by_type.items()):
        print(f"- {element_type.capitalize()}s: {len(elements)}")
    print(f"Total test functions: {total_tests}")
    print(f"Total files with tests: {total_files}")
    print("=" * 80)

def main():
    """Example usage with mock data."""
    try:
        # Example usage with django-10914
        instance_id = "django__django-10914"
        json_file = "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/edit_location_individual/loc_merged_0-0_outputs.json"
        
        results = find_element_tests(instance_id, json_file)
        print(results)
        print_test_results(results)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    main()
