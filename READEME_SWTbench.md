`./agentless/test/generate_reproduction_tests.py` 中 gen_test 函数中的逻辑是： 
对 issue 中的问题描述进行处理，然后调用 LLM 生成 reproduction 测试， temperature 为 0 生成 greedy 样本， 其他为 temperature sampling 生成多个样本。

我们现在要修改为，不仅加入对**问题的描述**进行处理，还要加入对**相关代码**进行处理。
在之前我们找到的定位到相关代码的文件，在 results/swe-bench-lite/edit_location_individual/loc_merged_{num}-{num}_outputs.json 中，" found_related_locs" 字段中，记录了每个文件中相关的代码。
遍历每个文件，将每一个文件中的相关代码提取出来，通过追踪技术追踪到相关的测试代码，然后将覆盖这部分代码的测试代码也加入 prompt 中。

然后调用 LLM 生成 reproduction 测试， temperature 为 0 生成 greedy 样本（一组测试）， 其他为 temperature sampling 生成 39 个样本。如果有 4 个可选的 edit_loc ，则生成 160 个样本。

在测试生成完成后，我们将测试结果保存到 results/swe-bench-lite/reproduction_individual/reproduction_merged_{num}-{num}_outputs.json 中。然后将测试加入原代码中，对一组测试，测试的输出结果保存到 results/swe-bench-lite/reproduction_individual/reproduction_merged_{num}-{num}_outputs.json 中。 然后对输出结果进行聚类，输出结果相同的测试为一类，最后根据聚类的数量进行排序，输出结果。





