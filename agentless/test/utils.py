import json

def find_edit_location_file(instance_id: str) -> dict:
    """
    根据instance_id查找对应的编辑位置文件路径
    
    Args:
        instance_id: 问题实例ID
        
    Returns:
        str: 编辑位置文件的完整路径
    """
    import os

    base_dir = "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/edit_location_individual"
    # 遍历所有文件
    related_locs_list = []
    
    for i in range(0, 100):  # 假设最多100个文件
        file_path = os.path.join(base_dir, f"loc_merged_{i}-{i}_outputs.json")
        if os.path.exists(file_path):
            # 打开文件
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data["instance_id"] == instance_id:
                    related_locs = data["found_related_locs"]
                    # 遍历 related_locs 中的 key 和 value
                    for key, value in related_locs.items():
                        test_func  = find_related_test_functions(key, value)
                        related_locs[key] = {
                            "test_functions": test_func,
                            "related_items": value
                        }
                    related_locs_list.append(related_locs)
    return related_locs_list
        

def find_related_test_functions(file_path: str, related_items: list) -> list:
    """
    遍历 found_related_locs 中的内容，定位相关的测试函数
    
    Args:
        file_path: 文件路径
        related_items: 相关内容
    """
    test_functions = []

    """
        TODO 寻找测试用例的相关逻辑
    """
    # MOCK
    if file_path == "django/core/files/storage.py":
        return '''
    class FileSystemStorageTests(unittest.TestCase):

      def test_deconstruction(self):
          path, args, kwargs = temp_storage.deconstruct()
          self.assertEqual(path, "django.core.files.storage.FileSystemStorage")
          self.assertEqual(args, ())
          self.assertEqual(kwargs, {'location': temp_storage_location})

          kwargs_orig = {
              'location': temp_storage_location,
              'base_url': 'http://myfiles.example.com/'
          }
          storage = FileSystemStorage(**kwargs_orig)
          path, args, kwargs = storage.deconstruct()
          self.assertEqual(kwargs, kwargs_orig)

      def test_lazy_base_url_init(self):
          """
          FileSystemStorage.__init__() shouldn't evaluate base_url.
          """
          storage = FileSystemStorage(base_url=reverse_lazy('app:url'))
          with self.assertRaises(NoReverseMatch):
              storage.url(storage.base_url)
'''
    if file_path == "django/core/files/uploadedfile.py":
        return '''
    class InMemoryUploadedFileTests(unittest.TestCase):
      def test_open_resets_file_to_start_and_returns_context_manager(self):
          uf = InMemoryUploadedFile(StringIO('1'), '', 'test', 'text/plain', 1, 'utf8')
          uf.read()
          with uf.open() as f:
              self.assertEqual(f.read(), '1')

    class TemporaryUploadedFileTests(unittest.TestCase):
      def test_extension_kept(self):
          """The temporary file name has the same suffix as the original file."""
          with TemporaryUploadedFile('test.txt', 'text/plain', 1, 'utf8') as temp_file:
              self.assertTrue(temp_file.file.name.endswith('.upload.txt'))
'''
    else:
        return ''


def gen_prompt(problem_statement: str, related_locs_item: dict) -> str:
    # 使用 join 方法和生成器表达式来构造每个文件的详情字符串
    prompt_files = ""
    for file_path, value in related_locs_item.items():
        prompt_files += f"File: {file_path}\nRelated items: {value['related_items']}\nTest functions: {value['test_functions']}\n"


    generate_tests_prompt_template = f"""
We are currently solving the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

We have found the bug code and the related test functions in the following files:
{prompt_files}

Please generate a complete test based on the provided test that can be used to reproduce the issue. 
Understood the existed test functions could help you generate the new test.
The generated test should be able to be used to both reproduce the issue as well as to verify the issue has been fixed.


The complete test should contain the following:
1. Necessary imports
2. Code to reproduce the issue described in the issue text

Please ensure the generated test reflects the issue described in the provided issue text.
The generated test should be able to be used to both reproduce the issue as well as to verify the issue has been fixed.
Wrap the complete test in ```python...```.
"""
    return generate_tests_prompt_template
