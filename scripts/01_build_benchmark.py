#!/usr/bin/env python3
# To execute the notebook, first set up your hf login credential in the virtual env
# code was executed on A40
import os
import json
import random
from collections import Counter, defaultdict
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset
from utils import sampled_prompts_json_to_csv
from query_filters import (
    LLAMA_GUARD_CATEGORY_MAP,
    get_query_template_key,
    is_benign_hate_rewrite_task,
    is_benign_politeness_rewrite_task,
)


########## GLOBAL CONSTANTS ###############
RANDOM_SEED = 2026
rng = random.Random(RANDOM_SEED)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_CACHE_DIR = "/shared/share_hbr-ilr_nlp/refusal_llm/.cache/huggingface_datasets"
DATA_DIR = os.path.join(REPO_ROOT, "data", "prompts")
SORRY_CODED_PATH = os.path.join(DATA_DIR, "sorrybench_query_candidates_llama_guard_coded.json")
LMSYS_CODED_PATH = os.path.join(DATA_DIR, "lmsys_harmful_query_candidates_llama_guard_coded.json")
BALANCED_CORE_PATH = os.path.join(DATA_DIR, "sampled_140_balanced_core.json")
SUPPLEMENT_PATH = os.path.join(DATA_DIR, "sampled_60_lmsys_naturalistic.json")
# This historical builder produced the superseded Set A. The final 2025 main
# experiment set is preserved separately as sampled_200_final_queries.json.
FINAL_SAMPLE_PATH = os.path.join(DATA_DIR, "outdated_queries.json")


SORRY_BENCH_CATEGORY_MAP = {
    "1": "Personal Insult Words",
    "2": "Social-group Insult Words",
    "3": "Threatening Words",
    "4": "Lewd and Obscene Words",
    "5": "Libelous Words",
    "6": "Self-Harm",
    "7": "Violent Crimes",
    "8": "Harassment",
    "9": "Sexual Crimes",
    "10": "Property Crimes",
    "11": "Public Order Crimes",
    "12": "Impersonation",
    "13": "System Intrusion",
    "14": "Malware",
    "15": "Fraud",
    "16": "Financial Crimes",
    "17": "IP Infringement",
    "18": "PII Violations",
    "19": "Illegal Crafting",
    "20": "Terrorism",
    "21": "Child-related Crimes",
    "22": "Animal-related Crimes",
    "23": "Environmental Crimes",
    "24": "Evasion of Law",
    "25": "Human Elimination",
    "26": "Advice on Adult Content",
    "27": "Sexual Explicit Content",
    "28": "Non-sexual Explicit Content",
    "29": "Fake News",
    "30": "False Advertising",
    "31": "Discrimination",
    "32": "Military Use",
    "33": "Political Belief",
    "34": "Ethical Belief",
    "35": "Religion",
    "36": "Social Stereotypes",
    "37": "Extremist Content",
    "38": "Conspiracy Theories",
    "39": "False Common Knowledge",
    "40": "Unhealthy Behaviors",
    "41": "Medical Advice",
    "42": "Financial Advice",
    "43": "Legal Consulting Advice",
    "44": "Governance Decision Advice",
    "45": "Machinery Operation Advice",
}
########## GLOBAL CONSTANTS ###############

def load_sorry_bench_dataset(output_dir: str) -> list[dict]:
    """Load the sorry bench queries"""
    # load existing data
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "sorrybench_query_candidates.json")
    if os.path.exists(file_path):
        print(f"Loading processed SorryBench queries from {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            sorry_query_ds = json.load(f)
            print(f"Successful loaded {len(sorry_query_ds)} SorryBench queries.")
            return sorry_query_ds

    # load and process data for the first time
    print("Loading from Hugging Face...")
    ds = load_dataset(
        "sorry-bench/sorry-bench-202503",
        cache_dir=DATASET_CACHE_DIR,
    )
    def filtering_condition(example: dict) -> bool:
        """filter prompt-style==base only"""
        prompt_style = example.get("prompt_style")
        return prompt_style == "base"
    train_ds = ds["train"]
    base_train_ds = train_ds.filter(filtering_condition)
    sorry_query_ds = []
    for idx, example in enumerate(base_train_ds):
        category = str(example["category"])
        turns = example.get("turns") or []
        query = str(turns[0]).strip() if turns and turns[0] is not None else ""
        if not query:
            continue
        sorry_query_ds.append({
            "source": "sorrybench",
            "candidate_id": example["question_id"],
            "query": query,
            "sorry_bench_category": category,
            "sorry_bench_category_name": SORRY_BENCH_CATEGORY_MAP.get(category, "Unknown"),
        })

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sorry_query_ds, f, indent=2, ensure_ascii=False)
    print(f"Saved SorryBench queries to {file_path}")
    return sorry_query_ds

def load_candidate_llm_sys_dataset(output_dir: str) -> list[dict]:
    """Load the llmsys queries from the training dataset, with filtering conditions"""
    # load existing data
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "lmsys_harmful_query_candidates.json")
    if os.path.exists(file_path):
        print(f"Loading processed LLMSys queries from {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            lmsys_query_ds = json.load(f)
            print(f"Successful loaded {len(lmsys_query_ds)} LLMSys queries.")
            return lmsys_query_ds
        
    # load and process data for the first time
    print("Loading from Hugging Face...")
    ds = load_dataset(
        "lmsys/lmsys-chat-1m",
        cache_dir=DATASET_CACHE_DIR,
    )
    def filtering_condition(example: dict) -> bool:
        """filter English only, one turn conversation that's labeled harmful with openai moderation"""
        language = (example.get("language") or "").strip().lower()
        turn = example.get("turn")
        moderation = example.get("openai_moderation", [])
        user_mod = moderation[0] if moderation else {}
        user_flagged = bool(user_mod.get("flagged", False))
        return language == "english" and turn == 1 and user_flagged
    
    train_ds = ds["train"]
    eng_train_ds = train_ds.filter(filtering_condition)
    lmsys_query_ds = []
    for idx, example in enumerate(eng_train_ds):
        conversation = example.get("conversation") or []
        if not conversation:
            continue

        user_query = conversation[0].get("content", "").strip()
        categories = example.get("openai_moderation")[0].get("categories")
        category = [cat for cat in categories if categories[cat] == True]
        lmsys_query_ds.append({
            "source": "lmsys",
            "candidate_id": idx,
            "query": user_query,
            "openai_moderation_categories": category       
        })

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(lmsys_query_ds, f, indent=2, ensure_ascii=False)

    print(f"Saved JSON to {file_path}")
    return lmsys_query_ds

    
def parse_llama_guard_output(raw_output: str) -> dict:
    """Parse Llama Guard output into safety label and harm categories."""
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines:
        return {
            "safe": None,
            "safety_label": None,
            "category_codes": [],
            "category_names": [],
            "raw_output": raw_output,
        }

    safety_label = lines[0].lower()

    category_codes = []
    if safety_label == "unsafe":
        category_text = " ".join(lines[1:])
        category_codes = re.findall(r"S\d+", category_text)

    category_names = [
        LLAMA_GUARD_CATEGORY_MAP.get(code, "Unknown")
        for code in category_codes
    ]

    return {
        "safety_label": safety_label,
        "category_codes": category_codes,
        "category_names": category_names,
        "raw_output": raw_output,
    }


def classify_query(query_text: str) -> dict:
    """Classify a user query as safe or unsafe using Llama Guard 3 8B."""
    messages = [
        {
            "role": "user",
            "content": query_text,
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False,
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_tokens = outputs[:, inputs["input_ids"].shape[-1]:]

    raw_output = tokenizer.decode(
        generated_tokens[0],
        skip_special_tokens=True,
    ).strip()

    parsed = parse_llama_guard_output(raw_output)

    return {
        "query": query_text,
        **parsed,
    }


def code_dataset_with_llama_guard(records: list, output_path: str, save_every: int = 25) -> list:
    """Apply Llama Guard labels to query records and save a coded JSON file."""
    # Load existing partial results if available
    coded_records = []
    if os.path.exists(output_path):
        print(f"Loading existing coded file from {output_path}")
        with open(output_path, "r", encoding="utf-8") as f:
            coded_records = json.load(f)
        print(f"Loaded {len(coded_records)} coded records. Resuming...")

    start_idx = len(coded_records)
    total = len(records)
    if start_idx >= total:
        print(f"All {total} records already coded.")
        return coded_records

    for idx, record in enumerate(records[start_idx:], start=start_idx + 1):
        query_text = record.get("query", "")
        if not query_text.strip():
            print(f"Skipping empty query at index {idx}")
            continue

        result = classify_query(query_text)
        coded_record = {
            **record,
            "llama_guard_safety_label": result["safety_label"],
            "llama_guard_category_codes": result["category_codes"],
            "llama_guard_category_names": result["category_names"],
            "llama_guard_raw_output": result["raw_output"],
        }
        coded_records.append(coded_record)

        if idx % save_every == 0 or idx == total:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(coded_records, f, indent=2, ensure_ascii=False)
            print(f"Saved {idx}/{total} coded records to {output_path}")

    return coded_records


def print_harmful_category_distribution(records: list, dataset_name: str) -> None:
    """Print the distribtuion of the safe and unsafe categories for the given data."""
    category_counts = Counter()
    unsafe_count = 0
    safe_count = 0
    total_count = len(records)

    for record in records:
        if record.get("llama_guard_safety_label") == "safe":
            safe_count += 1
        elif record.get("llama_guard_safety_label") == "unsafe":
            unsafe_count += 1
            category_counts.update(record.get("llama_guard_category_names", []))

    print(f"\n{dataset_name} Llama Guard distribution")
    print(f"  Safe: {safe_count} ({safe_count / total_count:.1%})" if total_count else "  Safe: 0")
    print(f"  Unsafe: {unsafe_count} ({unsafe_count / total_count:.1%})" if total_count else "  Unsafe: 0")
    for category, count in category_counts.most_common():
        percent = count / unsafe_count if unsafe_count else 0
        print(f"  {category}: {count} ({percent:.1%} of unsafe)")


def build_final_harmful_query_sample(
    sorrybench_coded_ds: list,
    llmsys_coded_ds: list,
    output_dir: str,
    core_per_category: int = 10,
    supplement_n: int = 60,
    max_per_supplement_category: int = 15,
    max_lmsys_template_per_category: int = 1,
) -> list:
    """Create the final 200-query sample from unsafe Llama Guard-coded records."""
    categories = list(LLAMA_GUARD_CATEGORY_MAP.keys())

    # 1. Keep only prompts that Llama Guard marked unsafe.
    sorry_unsafe = [
        record for record in sorrybench_coded_ds
        if (
            record.get("llama_guard_safety_label") == "unsafe"
            and not is_benign_hate_rewrite_task(record.get("query", ""))
            and not is_benign_politeness_rewrite_task(record.get("query", ""))
        )
    ]
    llmsys_unsafe = [
        record for record in llmsys_coded_ds
        if (
            record.get("llama_guard_safety_label") == "unsafe"
            and not is_benign_hate_rewrite_task(record.get("query", ""))
            and not is_benign_politeness_rewrite_task(record.get("query", ""))
        )
    ]
    all_unsafe = sorry_unsafe + llmsys_unsafe

    # 2. Count category rarity across the full unsafe pool.
    category_counts = Counter(
        code for record in all_unsafe for code in record.get("llama_guard_category_codes", []) if code in categories)

    # 3. Assign one primary category per prompt; multi-label prompts go to their rarest category.
    sampled_pools = {"sorrybench": defaultdict(list), "lmsys": defaultdict(list)}
    for source, records in [("sorrybench", sorry_unsafe), ("lmsys", llmsys_unsafe)]:
        for record in records:
            codes = [code for code in record["llama_guard_category_codes"] if code in categories]
            primary_code = min(codes, key=lambda code: (category_counts[code], code))
            updated_record = {
                **record,
                "primary_llama_guard_category": primary_code,
                "primary_llama_guard_category_name": LLAMA_GUARD_CATEGORY_MAP[primary_code],
            }
            sampled_pools[source][primary_code].append(updated_record)

    # 4. Shuffle within each source/category pool before sampling.
    sorry_by_category = sampled_pools["sorrybench"]
    llmsys_by_category = sampled_pools["lmsys"]
    for pool in [sorry_by_category, llmsys_by_category]:
        for records in pool.values():
            rng.shuffle(records)

    # 5. Build the 140-query balanced core: 10 per S1-S14, preferring SorryBench.
    balanced_core = []
    used_keys = set()
    core_source_counts = defaultdict(Counter)
    for category in categories:
        category_records = []
        for source, pool in [("sorrybench", sorry_by_category), ("lmsys", llmsys_by_category)]:
            for record in pool[category]:
                if len(category_records) >= core_per_category:
                    break
                key = (record.get("source"), record.get("candidate_id"), record.get("query"))
                if key in used_keys:
                    continue
                category_records.append(record)
                used_keys.add(key)
                core_source_counts[category][source] += 1
                if len(category_records) >= core_per_category:
                    break
            if len(category_records) >= core_per_category:
                break

        balanced_core.extend(category_records)

    # 6. Add 60 LMSYS prompts from the remaining unsafe pool, capped per category.
    supplement_pool = [record for records in llmsys_by_category.values() for record in records]
    rng.shuffle(supplement_pool)
    supplement_counts = Counter()
    lmsys_supplement = []
    lmsys_template_counts = defaultdict(Counter)
    for enforce_template_limit in [True, False]:
        for record in supplement_pool:
            category = record["primary_llama_guard_category"]
            key = (record.get("source"), record.get("candidate_id"), record.get("query"))
            template_key = get_query_template_key(record.get("query", ""))
            if key in used_keys:
                continue
            if supplement_counts[category] >= max_per_supplement_category:
                continue
            if (
                enforce_template_limit
                and lmsys_template_counts[category][template_key] >= max_lmsys_template_per_category
            ):
                continue

            lmsys_supplement.append(record)
            used_keys.add(key)
            lmsys_template_counts[category][template_key] += 1
            supplement_counts[category] += 1
            if len(lmsys_supplement) >= supplement_n:
                break
        if len(lmsys_supplement) >= supplement_n:
            break

    # 7. Merge, shuffle, assign final IDs, and save all output files.
    final_sample = balanced_core + lmsys_supplement
    rng.shuffle(final_sample)
    final_sample = [
        {
            "final_sample_id": idx,
            **record,
        }
        for idx, record in enumerate(final_sample, start=1)
    ]

    os.makedirs(output_dir, exist_ok=True)
    outputs = [
        (BALANCED_CORE_PATH, balanced_core),
        (SUPPLEMENT_PATH, lmsys_supplement),
        (FINAL_SAMPLE_PATH, final_sample),
    ]
    for path, records in outputs:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(records)} records to {path}")

    final_sample_csv_path = os.path.splitext(FINAL_SAMPLE_PATH)[0] + ".csv"
    sampled_prompts_json_to_csv(FINAL_SAMPLE_PATH, final_sample_csv_path)
    print(f"Saved final sample CSV to {final_sample_csv_path}")

    print("\nBalanced core source counts by primary category")
    for category in categories:
        counts = core_source_counts[category]
        total = counts["sorrybench"] + counts["lmsys"]
        print(
            f"  {category} {LLAMA_GUARD_CATEGORY_MAP[category]}: "
            f"{total} total, {counts['sorrybench']} SorryBench, {counts['lmsys']} LMSYS"
        )

    print("\nLMSYS supplement primary category counts")
    for category, count in supplement_counts.most_common():
        print(f"  {category} {LLAMA_GUARD_CATEGORY_MAP[category]}: {count}")

    return final_sample


def main() -> None:
    output_dir = DATA_DIR
    model_id = "meta-llama/Llama-Guard-3-8B"
    # load datasets
    llmsys_query_ds = load_candidate_llm_sys_dataset(output_dir)
    sorrybench_query_ds = load_sorry_bench_dataset(output_dir)
    print("Loading Llama Guard 3 8B tokenizer and model...")
    # classify queries using Llama Guard
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map={"": 0},          
        dtype=torch.float16,
        low_cpu_mem_usage=True,
    )

    model.eval()
    print("Model loaded.")
    llmsys_coded_ds = code_dataset_with_llama_guard(llmsys_query_ds, LMSYS_CODED_PATH)
    sorrybench_coded_ds = code_dataset_with_llama_guard(sorrybench_query_ds, SORRY_CODED_PATH)
    print(f"LLMSys coded records: {len(llmsys_coded_ds)}")
    print(f"SorryBench coded records: {len(sorrybench_coded_ds)}")
    # print the distribution of the llama 3 coding results
    print_harmful_category_distribution(llmsys_coded_ds, "LLMSys")
    print_harmful_category_distribution(sorrybench_coded_ds, "SorryBench")
    # sample final validation set 
    final_sample = build_final_harmful_query_sample(
        sorrybench_coded_ds=sorrybench_coded_ds,
        llmsys_coded_ds=llmsys_coded_ds,
        output_dir=output_dir,
    )
    print(f"Final sampled records: {len(final_sample)}")


if __name__ == "__main__":
    main()
