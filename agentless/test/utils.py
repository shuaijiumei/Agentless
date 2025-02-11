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
    
    base_dir = "../../results/swe-bench-lite/edit_location_samples"
    file_path = os.path.join(base_dir, f"{instance_id}_outputs.json")
    
    if not os.path.exists(file_path):
        return {}
        
    with open(file_path) as f:
        data = json.load(f)
        
    if data["instance_id"] != instance_id:
        return {}
        
    # 过滤掉以_traj结尾的键
    filtered_data = {k:v for k,v in data.items() if not k.endswith('_traj')}
    
    return filtered_data

def find_related_test_functions(filtered_data: dict) -> list:
    """
    遍历 found_related_locs 中的内容，定位相关的测试函数
    
    Args:
        filtered_data: 过滤后的定位数据字典
        
    Returns:
        list: 包含测试函数信息的列表，每个元素是一个字典，包含文件路径和相关内容
    """
    test_functions = []
    
    if "found_related_locs" not in filtered_data:
        return test_functions
        
    related_locs = filtered_data["found_related_locs"]

    for file_path, related_items in related_locs.items():
        test_functions.append({
            "file_path": file_path,
            "related_items": related_items
        })
    '''
    相关类： 
    FileSystemStorage
    测试用例：
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
    
    相关类：
    InMemoryUploadedFile
    测试用例：
    class InMemoryUploadedFileTests(unittest.TestCase):
      def test_open_resets_file_to_start_and_returns_context_manager(self):
          uf = InMemoryUploadedFile(StringIO('1'), '', 'test', 'text/plain', 1, 'utf8')
          uf.read()
          with uf.open() as f:
              self.assertEqual(f.read(), '1')

    相关类：
    TemporaryUploadedFile
    测试用例：
    class TemporaryUploadedFileTests(unittest.TestCase):
      def test_extension_kept(self):
          """The temporary file name has the same suffix as the original file."""
          with TemporaryUploadedFile('test.txt', 'text/plain', 1, 'utf8') as temp_file:
              self.assertTrue(temp_file.file.name.endswith('.upload.txt'))
    ''' 


    return test_functions
