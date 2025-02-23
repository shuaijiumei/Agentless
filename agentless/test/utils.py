import json
from trace_test import find_element_tests
import os
from logging import Logger
def find_edit_location_file(instance_id: str, logger: Logger) -> dict:
    """
    根据instance_id查找对应的编辑位置文件路径
    
    Args:
        instance_id: 问题实例ID
        
    Returns:
        str: 编辑位置文件的完整路径
    """

    base_dir = "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/edit_location_individual"
    cache_dir = "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/reproduction_test_samples/cache.json"
    related_test_list = []
    # 先获取目录下所有文件
    files = os.listdir(base_dir)
    # 筛选出符合格式的文件并获取最大索引
    max_index = -1
    for file in files:
        if file.startswith("loc_merged_") and file.endswith("_outputs.jsonl"):
            try:
                index = int(file.split("_")[2].split("-")[0])
                max_index = max(max_index, index)
            except:
                continue
    
    # 遍历实际存在的文件范围
    for i in range(0, max_index + 1):
        file_path = os.path.join(base_dir, f"loc_merged_{i}-{i}_outputs.jsonl")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    item = json.loads(line.strip())
                    if item.get('instance_id') == instance_id:
                        related_test = find_element_tests(instance_id, item.get('found_related_locs'), cache_dir, logger)
                        related_test_list.append(related_test)
    return related_test_list
        


def gen_prompt(problem_statement: str, related_locs_item: dict, instance_id: str) -> str:
    # 使用 join 方法和生成器表达式来构造每个文件的详情字符串

    prompt_files = ""
    for related_item in related_locs_item:
        test_str = "Related Tests: \n" if len(related_item['tests']) > 0 else ""
        prompt_files += f'''Related Item: {related_item['element_type']}: {related_item['element_name']}
{test_str}'''
        for test in related_item['tests']:
            prompt_files += f'''{test['code']}\n'''
    
    generate_tests_prompt_template = f"""
We are addressing the following issue in our repository: 
--- BEGIN ISSUE --- 
{problem_statement}
 --- END ISSUE ---

We have identified the bug and related test functions in the following files: 
{prompt_files}

Please generate a new test based on the provided test that can be used to:
1. Reproduce the issue described above
2. Verify that the issue has been fixed

**Test requirements:**
1. The test should be able to both reproduce the issue and validate its resolution.
2. The test should only contain the code necessary to reproduce the issue, excluding any existing test code.
3. Include the necessary imports.
4. Wrap the complete test in python....
Ensure that the generated test accurately reflects the issue described in the provided issue text.
"""
    if not os.path.exists("test_generation_prompt"):
        os.makedirs("test_generation_prompt")
    with open(os.path.join("test_generation_prompt", f"{instance_id}.txt"), "w") as f:
        f.write(generate_tests_prompt_template)
    return generate_tests_prompt_template


if __name__ == "__main__":
    instance_id = "django__django-10914"
    related_test_list = find_edit_location_file(instance_id)
    problem_statement = 'hello world'
    for item in related_test_list:
        prompt = gen_prompt(problem_statement, item)
        with open("prompt.txt", "w") as f:
            f.write(prompt)
