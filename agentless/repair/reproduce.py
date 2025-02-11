#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproduce.py - 用于生成测试并复现 Github issue 中提到的问题

该脚本基于 repair.py 的思路构建，通过解析定位文件（loc_file）和数据集，提取问题描述，生成一个复现测试摘要文件，
以便复现 Github issue 中提到的问题。

使用示例:
    python reproduce.py --loc_file loc.jsonl --output_folder ./output [其他参数...]
    其他参数和 repair.py 的参数保持一致。
"""

import argparse
import json
import os
from datasets import load_dataset


def load_jsonl(file_path):
    """加载 jsonl 文件，每行作为一个 JSON 对象."""
    results = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                results.append(obj)
            except Exception as e:
                print(f"加载行时出错: {e}")
    return results


def generate_test(args):
    """生成用于复现 Github issue 的测试摘要文件."""
    # 确保输出文件夹存在
    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)

    # 加载定位文件
    locs = load_jsonl(args.loc_file)
    if not locs:
        print("未能加载loc文件，退出。")
        return

    # 如果提供 target_id，则选取匹配的记录，否则选取第一个
    selected_loc = None
    if args.target_id:
        for loc in locs:
            if "instance_id" in loc and loc["instance_id"] == args.target_id:
                selected_loc = loc
                break
        if not selected_loc:
            print(f"未找到 target_id 为 {args.target_id} 的记录，退出。")
            return
    else:
        selected_loc = locs[0]

    instance_id = selected_loc.get("instance_id", "unknown")

    # 加载数据集
    try:
        swe_bench_data = load_dataset(args.dataset, split="test")
    except Exception as e:
        print(f"加载数据集时出错: {e}")
        return

    bench_data = None
    for item in swe_bench_data:
        if "instance_id" in item and item["instance_id"] == instance_id:
            bench_data = item
            break
    if not bench_data:
        print(f"在数据集中未找到 instance_id 为 {instance_id} 的记录。")
        return

    problem_statement = bench_data.get("problem_statement", "无问题描述")

    # 生成测试摘要内容
    summary = f"""
复现测试摘要
-----------------------
实例ID: {instance_id}
问题描述:
{problem_statement}
-----------------------
"""

    print(summary)

    # 将摘要写入输出文件
    output_path = os.path.join(args.output_folder, "reproduce_test.txt")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"测试摘要已写入: {output_path}")
    except Exception as e:
        print(f"写入测试摘要时出错: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loc_file", type=str, required=True, help="定位文件路径 (jsonl格式)")
    parser.add_argument("--top_n", type=int, default=1, help="top_n")
    parser.add_argument("--loc_interval", action="store_true", help="是否使用 loc_interval")
    parser.add_argument("--context_window", type=int, default=10, help="上下文窗口大小")
    parser.add_argument("--gen_and_process", action="store_true", help="是否生成并处理")
    parser.add_argument("--max_samples", type=int, default=20, help="Sampling budget")
    parser.add_argument("--select_id", type=int, default=-1, help="选择处理样本的索引")
    parser.add_argument("--model", type=str, default="gpt-4o-2024-05-13", choices=["gpt-4o-2024-05-13", "deepseek-coder", "gpt-4o-mini-2024-07-18", "claude-3-5-sonnet-20241022"], help="模型名称")
    parser.add_argument("--backend", type=str, default="openai", choices=["openai", "deepseek", "anthropic"], help="后端类型")
    parser.add_argument("--output_folder", type=str, required=True, help="输出文件夹")
    parser.add_argument("--post_process", action="store_true", help="是否进行后处理")
    parser.add_argument("--add_space", action="store_true", help="是否添加空格")
    parser.add_argument("--cot", action="store_true", help="是否使用 Cot 模式")
    parser.add_argument("--fine_grain_loc_only", action="store_true", help="是否仅使用细粒度定位")
    parser.add_argument("--diff_format", action="store_true", help="是否使用 diff 格式")
    parser.add_argument("--str_replace_format", action="store_true", help="是否使用字符串替换格式")
    parser.add_argument("--skip_greedy", action="store_true", help="是否跳过贪心采样")
    parser.add_argument("--sticky_scroll", action="store_true", help="是否使用粘性滚动")
    parser.add_argument("--num_threads", type=int, default=1, help="并发线程数")
    parser.add_argument("--target_id", type=str, help="目标实例ID")
    parser.add_argument("--mock", action="store_true", help="是否进行mock运行")
    parser.add_argument("--dataset", type=str, default="princeton-nlp/SWE-bench_Lite", choices=["princeton-nlp/SWE-bench_Lite", "princeton-nlp/SWE-bench_Verified"], help="数据集名称")
    args = parser.parse_args()

    generate_test(args)


if __name__ == "__main__":
    main() 