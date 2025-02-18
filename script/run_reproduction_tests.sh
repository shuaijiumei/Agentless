#!/bin/bash
# 定义包含 4 个目录的数组
folders=(
    "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/reproduction_test_samples/test_patch_0"
    # "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/reproduction_test_samples/test_patch_1"
    # "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/reproduction_test_samples/test_patch_2"
    # "/mnt/d/vscodeProject/Agentless/results/swe-bench-lite/reproduction_test_samples/test_patch_3"
)

counter_1=0
counter_2=0
# 遍历每个目录
for folder in "${folders[@]}"; do
    # 遍历该目录下所有名称符合 test_patch_*.json 的文件
    for file in "$folder"/test_patch_*.json; do
        echo "Processing file: ${file}"
        python agentless/test/run_reproduction_tests.py --run_id="reproduction_test_generation_filter_sample_${counter_1}_${counter_2}" \
                                                        --test_jsonl="${file}" \
                                                        --num_workers 6 \
                                                        --testing
        counter_2=$((counter_2+1))
    done
    counter_1=$((counter_1+1))
done
