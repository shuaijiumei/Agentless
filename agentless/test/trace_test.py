#!/usr/bin/env python3
import ast
import os
from typing import List, Tuple, Dict, Any, Literal
import datasets
from logging import Logger
from agentless.test.cache_manager import CacheManager
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

def find_element_tests(instance_id: str, found_related_locs: Dict[str, List[str]], cache_manager: CacheManager, logger: Logger, dataset_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main function to find test code for elements (classes, functions, variables).
    Args:
        instance_id: Instance ID from the dataset
        found_related_locs: Dictionary containing related locations
        cache_manager: Cache manager instance for thread-safe cache operations
        logger: Logger instance
    Returns:
        List of dictionaries containing test information
    """
    # Load element information
    element_info_list = []
    for file_path, items in found_related_locs.items():
        processed_items = [
            sub_item 
            for item in items
            for sub_item in (item.split("\n") if "\n" in item else [item])
        ]
        
        for item in processed_items:
            try:
                element_name, element_type = parse_element_info(item)
                element_info_list.append({
                    "name": element_name,
                    "type": element_type, 
                    "source_file": file_path
                })
            except ValueError:
                continue

    if not element_info_list:
        raise ValueError("Must contain valid element information")

    # 读取缓存
    cache_data = cache_manager.read()
        
    # 检查缓存
    for element_info in element_info_list:
        cache_key = "_".join([instance_id, element_info['source_file'], element_info['type'], element_info['name']])
        if cache_key in cache_data:
            element_info['tests'] = cache_data[cache_key]

    repo_name = dataset_item['repo']
    base_commit = dataset_item['base_commit']
    base_path = '/mnt/d/vscodeProject/Agentless/playground_manual/repo_commit'
    repo_path = os.path.join(base_path, f'{repo_name.split("/")[-1]}_{base_commit}')

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
                results_list[-1]['tests'] = tests
                
                # 更新缓存
                cache_key = "_".join([instance_id, element_info['source_file'], element_info['type'], element_info['name']])
                cache_manager.write(cache_key, tests)
                   
        return results_list
    except Exception as e:
        logger.error(f"Error finding tests for {instance_id}: {str(e)}")
        return []

