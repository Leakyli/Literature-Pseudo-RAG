---
create-date: 2026-07-05, 13:15:00
type: Project
tags:
  - literature-rag/synthesis
link:
status: active
order:
parent:
---
# Literature Synthesis: Token Optimization and Pruning Methods for Large Language Models

## References

[1] [[research_paper_1783255564_0]] — Algawiaz D. Hallucination-aware learning and latency optimization transformer (HALL-OPT) for real-time edge intelligence. *Sci Rep* (2026). https://doi.org/10.1038/s41598-026-42981-3

[2] [[research_paper_1783255596_1]] — Taylar J. Strategies for computational efficiency in small language models. *Auton. Intell. Syst.* **6**, 8 (2026). https://doi.org/10.1007/s43684-026-00130-7

[3] [[research_paper_1783255627_2]] — Wen JL, Li XJ, Yao JP, et al. Consensus-Expert DynamicMoE: ARIMA-based Capacity Prediction with Adaptive Load Balancing for Sparse Models. *Int J Comput Intell Syst* **19**, 157 (2026). https://doi.org/10.1007/s44196-026-01236-9

---

## Paper 1: HALL-OPT — Hallucination-Aware Learning and Latency Optimization Transformer for Real-Time Edge Intelligence [1]

**Venue:** *Scientific Reports* (2026) | DOI: 10.1038/s41598-026-42981-3  
**Author:** Danah Algawiaz (Shaqra University, Saudi Arabia)  
**Status:** Article in Press (Open Access, CC BY-NC-ND 4.0)  
**Code:** https://github.com/DanahAG-R/Hall-OPT/tree/main

### Core Contribution

HALL-OPT proposes a **unified framework** that jointly optimizes hallucination detection and latency reduction for transformer deployment on resource-constrained edge devices. Unlike prior work that treats reliability and efficiency as separate objectives, HALL-OPT integrates four tightly coupled modules into a single edge-optimized transformer architecture:

1. **Hallucination-Aware Attention Mechanism (HAAM)** — A dual-stream detector that analyzes internal attention behavior (attention entropy, output uncertainty, contextual consistency) to estimate token-level hallucination risk *during inference* without external knowledge bases.
2. **Dynamic Token Pruning (DTP)** — An adaptive pruning system that computes token importance scores combining hidden-state salience, cumulative attention weight, and hallucination risk (1 − Hₜ), then prunes tokens below a dynamic per-layer threshold derived from the statistical distribution of importance scores.
3. **Adaptive Knowledge Distillation (AKD)** — A distillation pipeline that transfers both predictive capability and reliability behavior from a large teacher to a compact student, using a hallucination-aware loss that penalizes overconfident erroneous predictions.
4. **Edge Optimization Layer (EOL)** — Quantization-aware training (INT8) with hardware-aware deployment (TensorRT on Jetson AGX Xavier, Coral TPU) to enable sub-50ms inference on edge hardware.

### Key Technical Innovations

**Hallucination Score Formulation (Eq. 3):**  
Hₜ = α·ℰ(Aₜ) + β·𝒰(pₜ) + γ·𝒞(Aₜ, A_ctx)  
where α, β, γ are learnable weights (softmax-normalized, τ=0.5, bounds [0.1, 0.9]), converging to α≈0.28, β≈0.31, γ≈0.41 on SQuAD 2.0. Contextual consistency (γ) proves most decisive for detection accuracy (Table 6 sensitivity analysis).

**Dynamic Pruning Threshold (Eq. 10):**  
τ_prune = μₗ + σₗ · Φ⁻¹(ρ_target)  
Computed per-layer from the mean (μₗ) and std (σₗ) of token importance scores, with target retention ratio ρ_target dynamically adjusted per input based on hardware latency budget and input complexity.

**Training Algorithm (Alg. 1):** Joint optimization of task loss ℒ_task, hallucination loss ℒ_hall, distillation loss ℒ_distill, and feature loss ℒ_feat in a single loop. Hallucination detector parameters {α, β, γ, τ_hall} updated solely via ℒ_hall gradients.

**Inference Algorithm (Alg. 2):** Adaptive inference with latency budget T_max — applies aggressive pruning (lower τ_prune) when latency estimate exceeds budget.

### Experimental Validation

**Datasets:** SQuAD 2.0 (150K QA pairs with unanswerable questions) + CNN/DailyMail (300K news articles for abstractive summarization) — 463K total samples.

**Baselines (10):** BERT-base, DistilBERT, TinyBERT, MobileBERT, ALBERT, ELECTRA, DeBERTa, SAPLMA, MIND, TransKD, MobileViT-XS, LT-Mini.

**Hardware:** NVIDIA A100 (training), Jetson AGX Xavier / Coral TPU / Jetson Nano / Xavier NX / AGX Orin / RPi 4+TPU / RPi Zero 2W (deployment).

**Key Results (Table 3, 4, 5):**

| Metric | BERT-base | HALL-OPT | Improvement |
|--------|-----------|----------|-------------|
| SQuAD 2.0 F1 | 88.5% | **89.7%** | +1.2% |
| SQuAD 2.0 EM | 81.3% | **82.9%** | +1.6% |
| Hallucination Acc. (SQuAD) | 76.2% | **94.3%** | **+18.1%** |
| CNN/DM ROUGE-L | 38.1% | **41.2%** | +3.1% |
| Hallucination Acc. (CNN/DM) | 72.8% | **93.8%** | **+21.0%** |
| Latency (Jetson AGX Xavier) | 156.3ms | **50.3ms** | **−67.8%** |
| FLOPs (G) | 22.5 | **6.5** | **−71.3%** |
| Memory (MB) | 432 | **179** | **−58.6%** |
| Energy (mJ) | 892 | **268** | **−70.0%** |

**Hallucination Detection (Table 5):** HALL-OPT achieves 94.3% accuracy, 92.1% precision, 96.8% recall, 94.4% F1, 0.971 AUC, 0.051 FPR — outperforming dedicated detectors MIND (91.2% acc) and SAPLMA (88.7% acc).

**Ablation Study (Table 7):** Removing HAAM causes largest hallucination accuracy drop (−15.7%); removing DTP causes largest latency increase (+74.2%); removing AKD causes largest task accuracy drop (−4.4%); removing EOL increases latency +36% and energy +54%. Full integration is synergistic.

**Pruning Ratio Analysis (Fig. 6):** Optimal retention ratio ρ=0.45 yields 89.7% F1 at 50.3ms latency.

**Cross-Dataset Generalization (Table 10):** Train SQuAD → Test CNN/DM: HALL-OPT suffers only −6.1% accuracy drop vs. −10.8% mean for baselines, with 88.2% hallucination accuracy retention.

**Real-World Edge Deployment (Table 8):** Sub-50ms latency on Xavier NX (42.1ms), AGX Xavier (48.9ms), AGX Orin (31.2ms), Coral TPU (35.7ms). Average across 8 devices: 69.7ms latency, 87.9% accuracy, 389mJ energy.

**WCET Analysis:** Worst-case execution time 89.7ms on Jetson AGX Xavier (512 tokens, ρ=0.8, batch=16, thermal throttling). 99.3% deadline hit rate for 100ms deadline.

### Limitations Acknowledged

1. **Training overhead:** Multi-objective optimization increases training time/resources vs. single-objective compact models.
2. **Short-sequence diminishing returns:** Pruning benefits marginal when token redundancy is inherently low.
3. **Domain shift vulnerability:** Technical/specialized domains (biomedical, legal) may alter attention entropy patterns, reducing HAAM reliability.
4. **Architectural rigidity:** Fixed backbone depth/width may not suit extreme hardware heterogeneity.
5. **Representational depth requirement:** Ultra-tiny transformers may lack sufficient intermediate representations for reliable hallucination scoring.

### Failure Mode Quantification (5K samples/dataset)

| Failure Mode | SQuAD 2.0 | CNN/DM |
|-------------|-----------|--------|
| Subtle semantic distortion | 2.3% | 3.8% |
| Paraphrased misinformation | 1.1% | 2.4% |
| Numerical inflation | 0.8% | 1.9% |
| Long-range dependency miss | 1.4% | 2.1% |
| Technical term false positive | 0.9% | 0.7% |
| **Total** | **5.7%** | **10.1%** |

73% of failures involve >3 nested clauses or domain-term density >15%.

---

## Paper 2: Strategies for Computational Efficiency in Small Language Models [2]

**Venue:** *Autonomous Intelligent Systems* **6**, 8 (2026) | DOI: 10.1007/s43684-026-00130-7  
**Author:** Jonathan Taylar (National University, Manila, Philippines)  
**Published:** 09 April 2026 (Open Access, CC BY-NC-ND 4.0)

### Core Contribution

This work provides a **controlled empirical comparison and Pareto-based synthesis** across three orthogonal efficiency axes for Small Language Models (SLMs): (1) post-training quantization (numerical compression), (2) targeted knowledge distillation (capability transfer), and (3) architectural redesign (State-Space Models / Mamba). Unlike [1] which proposes a *unified integrated framework*, [2] evaluates these strategies *independently* under hardware/dataset/compute parity to derive a deployment-oriented decision framework.

### Three Orthogonal Efficiency Axes

| Axis | Strategy | Mechanism | Stage |
|------|----------|-----------|-------|
| **Numerical Compression** | 4-bit GPTQ Quantization | Layer-wise post-training quantization to INT4 | Post-training |
| **Capability Transfer** | Knowledge Distillation (GPT-4 → Gemma-2B) | Chain-of-thought distillation with KL-divergence loss | Fine-tuning |
| **Architectural Redesign** | Mamba (Selective SSM) | Linear-time recurrent inference, constant memory (no KV cache) | Pre-training |

### Experimental Design

**Baseline SLMs (16-bit):** Llama-3-8B (industry standard), Phi-3-mini-3.8B (high-quality data paradigm), Gemma-2B (efficient baseline).

**Benchmarks:** MMLU (general knowledge), GSM8K (multi-step reasoning), Perplexity (language modeling quality), Throughput (tokens/sec), Peak Memory Footprint (GB), On-disk Size (GB).

**Hardware:** NVIDIA A100 (primary), Jetson Orin (edge validation). *Note: Energy-per-token not directly measured; inferred from memory/throughput.*

**Controlled Variables:** Hardware parity, dataset parity, compute parity (FLOPs matched ±3% for Mamba training).

### Key Results

#### 1. 4-bit Quantization (GPTQ on Phi-3-mini) — **Most Effective Broad Strategy**
- **Memory footprint:** −71% reduction (peak GPU memory during 2048-token generation)
- **Throughput:** +83% increase
- **MMLU:** −1.2 pp (63.8% → 62.6%)
- **GSM8K:** −3.1 pp (more fragile reasoning benchmark)
- **Pareto Status:** Establishes new aggressive frontier — outperforms unquantized Gemma-2B and Mamba-SLM on memory-normalized accuracy

#### 2. Knowledge Distillation (GPT-4 → Gemma-2B on GSM8K) — **Targeted "Scalpel"**
- **GSM8K:** **+11.6 pp** uplift (surgical capability implantation)
- **General MMLU:** No significant improvement (confirms distillation is task-specific, not general-purpose)
- **Model size:** Unchanged (2B params)
- **Architecture:** Unchanged (Transformer)

#### 3. Mamba-SLM (3B, trained 300B tokens, compute-matched) — **Specialized Architecture**
- **MMLU/GSM8K:** Lower than Phi-3-mini (3.8B) at parameter parity
- **Throughput:** **Highest of all models tested** (KV cache-free recurrent design)
- **Memory scaling:** Constant w.r.t. context length (O(1) vs. Transformer O(n))
- **Trade-off:** Optimized for *raw generating speed* and *streaming/long-context*, not general accuracy

### Pareto Frontier Synthesis (Fig. 8)

The accuracy (MMLU) vs. inference memory footprint frontier is defined by two models:
1. **Llama-3-8B** — High-performance extreme
2. **Phi-3-mini 4-bit (GPTQ)** — High-efficiency extreme, **new state-of-the-art frontier**

The quantized Phi-3-mini delivers ~63.8% MMLU at <1/3 the memory of unquantized Phi-3-mini, dominating Gemma-2B and Mamba-SLM for memory-constrained deployment.

### Deployment Decision Framework (Section 6)

| Use Case | Recommended Strategy | Rationale |
|----------|---------------------|-----------|
| Broad on-device deployment (speed + memory critical) | **4-bit Quantization (GPTQ/AWQ)** on strong foundation (Phi-3/Llama-3) | Best efficiency/accuracy balance; Pareto-optimal |
| Specialized expert task (SQL, medical summarization, math) | **Knowledge Distillation** on small SLM (e.g., Gemma-2B) | Implants specific capability without size increase |
| Ultra-low latency/streaming/continuous inference | **Non-Transformer (Mamba/RWKV)** | O(1) inference step, no KV cache, constant memory |
| Future research | **Combine strategies** (e.g., 4-bit Mamba + distillation) | Potential "best of all worlds" |

### Limitations Acknowledged

1. Distillation evaluated only on GSM8K — broader reasoning generalization unverified (ARC-Challenge, HumanEval, BIG-Bench needed).
2. No direct energy-per-token profiling on edge hardware (inferred from memory/throughput).
3. Synthetic teacher data (GPT-4) may introduce stylistic artifacts despite filtering.
4. Pareto claims restricted to controlled experimental set; cross-publication comparisons confounded.
5. Parameter parity ≠ capacity parity across Transformer vs. SSM architectures (different inductive biases).

### Cross-Paper Connections with [1]

| Aspect | HALL-OPT [1] | Taylar et al. [2] | Synthesis |
|--------|--------------|-------------------|-----------|
| **Quantization** | INT8 QAT (edge deployment) | 4-bit GPTQ (post-training) | [1] uses QAT for hardware-aware edge deployment; [2] shows 4-bit GPTQ is Pareto-optimal for memory/accuracy. Complementary: QAT could further improve [2]'s quantized models. |
| **Distillation** | AKD with hallucination-aware loss | Standard KD (GPT-4 → Gemma) | [1] innovates by making distillation *reliability-aware*; [2] shows standard KD is a "scalpel" for specific skills. [1]'s approach could enhance [2]'s distillation for reliability-critical tasks. |
| **Architecture** | Optimized Transformer (pruned + distilled) | Mamba (SSM) alternative | [1] pushes Transformer efficiency to edge limits; [2] shows Mamba wins on throughput/streaming but loses on accuracy-memory Pareto. Different design points. |
| **Pruning** | Dynamic token pruning (DTP) at inference | Not evaluated (focus on quantization) | [1]'s DTP is orthogonal to [2]'s quantization — could be combined (quantized + pruned). |
| **Evaluation** | Edge hardware (Jetson, Coral, RPi) + WCET | A100 + Jetson Orin (no energy) | [1] provides more deployment-realistic validation (WCET, energy, 8 devices); [2] provides cleaner Pareto analysis. |

---

## Paper 3: Consensus-Expert DynamicMoE: ARIMA-based Capacity Prediction with Adaptive Load Balancing for Sparse Models [3]

**Venue:** *International Journal of Computational Intelligence Systems* **19**, 157 (2026) | DOI: 10.1007/s44196-026-01236-9  
**Authors:** Jia-Lin Wen, Xiao-Jun Li, Jun-Ping Yao, Hai-Feng Sun, Xiang-Rui An (Rocket Force University of Engineering, PLA Air Force Aviation University)  
**Published:** 12 March 2026 (Open Access, CC BY 4.0)  
**Funding:** Natural Science Basis Research Plan in Shaanxi Province (Grant No. 2025JC-YBMS-783)

### Core Contribution

This paper addresses **Mixture-of-Experts (MoE) load balancing** from a fundamentally different angle than [1] and [2]. Rather than optimizing a dense transformer via pruning/quantization/distillation, [3] tackles the *structural inefficiency* of sparse MoE architectures at the **training-time routing level**. The core innovation is a **dynamic expert capacity allocation mechanism** driven by **ARIMA time-series forecasting** of per-expert load, combined with a **prediction-aware loss function** that enforces *relative* (not absolute) load balance — preserving token-expert compatibility while preventing token overflow.

The method operates on **MoE models with consensus experts** (a dedicated expert that processes all tokens to capture shared knowledge, reducing parameter redundancy among specific experts — inspired by DeepSeekMoE [15]). Two key problems are solved jointly:
1. **Fixed expert capacity → token overflow during early-training routing fluctuations**
2. **Absolute-balance loss functions → forced redistribution that breaks token-expert semantic alignment**

### Key Technical Innovations

**Consensus Expert Architecture (Eq. 3):**  
The MoE layer designates N consensus experts (always active, process all tokens) and M-N specific experts (routed via Top-k). In Switch Transformer-base-8 configuration: 1 consensus expert + 7 specific experts with Top-2 routing (vs. vanilla Top-2 on 8 experts). This maintains constant activated parameter count while capturing common knowledge in the consensus expert.

**ARIMA Load Forecasting (Eq. 5–6):**  
Expert load per MoE layer is modeled as univariate time series xₜ. The paper demonstrates strong autocorrelation and temporal locality — load fluctuations are large early (iterations 1–3K), then stabilize. ARIMA(p,d,q) is fitted per-expert per-layer using historical loads. ARIMA outperforms Transformer-based predictors on FLOPs (orders of magnitude lower) and matches accuracy because expert load lacks long-range dependencies — it stabilizes quickly, making statistical models sufficient (Table 6).

**Dynamic Capacity Allocation (Alg. 1):**  
Before each routing step, ARIMA predicts next-iteration load distribution. Expert capacity factors Qᵢ are scaled proportionally to predicted loads:  
Capacityᵢ = (T/N) × Qᵢ × (predicted_loadᵢ / mean_predicted_load)  
This proactively expands capacity for experts forecasted to receive high load, preventing overflow without globally increasing capacity factor.

**Prediction-Aware Loss Function (Eq. 8):**  
ℒ_Total = λ₁·ℒ_Balance + λ₂·ℒ_Predict  
where ℒ_Balance = |fᵢ - l̂ᵢ| Σ fᵢPᵢ (weighted by prediction accuracy)  
and ℒ_Predict = MSE(fᵢ, l̂ᵢ) (prediction error)  
with fᵢ = actual token frequency routed to expert i, l̂ᵢ = normalized predicted load, Pᵢ = routing probability.  
The absolute difference |fᵢ - l̂ᵢ| acts as a *prediction-confidence-weighted penalty*: when prediction matches reality (high confidence), the balance penalty scales down, allowing natural load skew that reflects true token-expert affinity. When prediction is wrong, penalty increases to correct routing. λ₁=0.1, λ₂=0.01.

### Experimental Validation

**Dataset:** GLUE benchmark (9 NLU tasks: SST-2, CoLA, MRPC, QQP, STS-B, MNLI, RTE, QNLI, WNLI) — single-sentence, similarity, and inference tasks with varying class balance and data volumes (634 to 360K samples).

**Model:** Switch Transformer-base-8 (T5-base backbone, 12 layers, alternating MoE, 8 experts/layer, hidden=1280, heads=10, 128/head). Trained on single A100 (no distributed comms). Batch=1024, max_len=256, warmup 2K steps, step-decay at 80%/90%.

**Baselines:** 
- **ST-8vanilla**: Original Switch Transformer, Top-2 routing, original load-balance loss
- **ST-8consensus**: 1 consensus expert + Top-1 specific expert routing, original loss

**Scalability Tests:** Extended to 16 experts (1 consensus, Top-2) and 32 experts (2 consensus, Top-2).

### Key Results

**GLUE Average Accuracy (Table 4):**  
Proposed method: **81.55%** (+1.07% over ST-8vanilla, +0.5% over ST-8consensus)

**Per-Task Gains (Table 4):** Largest improvements on imbalanced/small-data tasks:
- MRPC (3.7K, 65% negative): **+1.8%** over vanilla
- WNLI (634, label-imbalanced): **+1.6%** over vanilla  
- RTE (3K): Notable gains
- QQP (360K, 63/37 split): Smaller gain (+0.3%) — rich data naturally balances load

**Scalability (Table 5):** Gains persist at 16 experts (+0.6% over consensus-only) and 32 experts (+0.6%). Method consistently outperforms consensus-only baselines across all three scales.

**ARIMA Prediction Quality (Fig. 2):** Prediction error rate stabilizes ~0.02% after ~6K iterations across all MoE layers. Shallow layers show higher early fluctuation but converge.

**Expert Specialization (Fig. 3):** Ablation disabling top-1 expert: consensus model shows **lower accuracy + higher variance** vs. vanilla, confirming *reduced redundancy* and *higher expert irreplaceability* — the intended specialization effect.

**Load Balancing Dynamics (Fig. 4):** 
- (a) Shallow layer load variance: high early, stabilizes ~3K iterations
- (b) Actual/Predicted load ratio → 1.0 by ~3K iterations across 8/16/32-expert configs, confirming dynamic capacity + loss function achieves relative balance

**Transformer vs. ARIMA Predictor (Table 6):** Transformer predictor uses far more FLOPs/params but yields no accuracy improvement on QQP/SST-2/RTE at 8/16 experts. At 32 experts on QQP, Transformer shows slight edge — but ARIMA's efficiency makes it the pragmatic choice.

### Limitations Acknowledged

1. **Scale:** Experiments on Switch-base (small MoE); unverified on trillion-parameter models (DeepSeek-V3, GLaM scale).
2. **Centralized training:** Single GPU; real large-scale MoE training is distributed (expert parallelism across devices) — inter-device load balancing unaddressed.
3. **Single-layer view:** No cross-layer load synergy mechanism; semantic hierarchies across layers unexploited.
4. **Homogeneous expert size:** All experts same capacity; heterogeneous experts (different sizes for different task difficulty) unexplored.
5. **Routing granularity:** Top-k only; token-adaptive variable-k routing (e.g., AdaMoE [38]) not integrated.

### Cross-Paper Synthesis: The Three Efficiency Paradigms

The three papers in this folder represent **three distinct but complementary paradigms** for LLM efficiency:

| Paradigm | Paper | Target | Mechanism | Stage |
|----------|-------|--------|-----------|-------|
| **Inference-Time Dense Model Compression** | [1] HALL-OPT | Dense Transformer on edge | Joint hallucination detection + token pruning + INT8 QAT + distillation | Inference + Training |
| **Post-Training / Fine-Tuning SLM Optimization** | [2] Taylar et al. | Small dense Transformers / SSMs | 4-bit quantization, targeted distillation, architectural swap (Mamba) | Post-training / Fine-tuning / Pre-training |
| **Training-Time Sparse Architecture Optimization** | [3] Wen et al. | MoE (Switch/DeepSeek style) | ARIMA dynamic capacity + prediction-aware loss + consensus experts | Pre-training / Training |

**Critical Interactions & Complementarities:**

1. **[1]'s DTP + [3]'s Dynamic Routing:** HALL-OPT prunes tokens *at inference* based on importance scores; [3] prevents token *overflow at training* via capacity prediction. They operate at different lifecycle stages but share the same core problem: **token-expert/token-layer mismatch**. A unified system could use [3]'s training-time load forecasts to inform [1]'s inference-time pruning thresholds.

2. **[2]'s Quantization + [3]'s MoE:** [2] shows 4-bit GPTQ is Pareto-optimal for dense SLMs. MoE models (like [3]'s Switch Transformer) are natural candidates for quantization — expert-specific quantization (different bits per expert based on load/specialization) is an open direction. [3]'s ARIMA load predictor could guide *which experts to quantize more aggressively* (low-load experts → lower precision).

3. **[1]'s HAAM + [3]'s Consensus Experts:** HALL-OPT's hallucination detector analyzes attention entropy/uncertainty. In MoE, the **consensus expert** by definition processes all tokens and sees global context — it could serve as a natural *hallucination sentinel* for the entire MoE layer, feeding signals to both [1]-style pruning and [3]-style routing.

4. **[2]'s Distillation + [3]'s Expert Specialization:** [3] proves consensus experts reduce parameter redundancy and increase expert specialization (Fig. 3). [2] shows distillation is a "scalpel" for specific capabilities. **Distilling into specialized experts** (rather than a monolithic student) could yield a "Mixture of Distilled Experts" — each expert learns a distilled capability slice.

5. **Evaluation Gaps:** [1] excels at edge deployment realism (WCET, energy, 8 devices). [2] excels at clean Pareto analysis. [3] lacks both — single GPU, no energy, no edge deployment. **Future work should benchmark [3]'s DynamicMoE on Jetson/Orin with quantization ([2]) and pruning ([1]) applied.**

---

## Unified Literature Matrix

| Dimension | HALL-OPT [1] | Taylar et al. [2] | Wen et al. [3] |
|-----------|--------------|-------------------|----------------|
| **Primary Target** | Dense Transformer edge inference | Small Language Models (dense + SSM) | MoE Training (Switch/DeepSeek) |
| **Efficiency Lever** | Inference-time pruning + INT8 QAT | Post-training quantization, KD, architecture | Dynamic capacity + prediction-aware loss |
| **Reliability Focus** | Hallucination detection (HAAM) | Task-specific capability (distillation) | Expert specialization (consensus + balance) |
| **Key Innovation** | Joint hallucination+latency optimization | Pareto synthesis of 3 orthogonal axes | ARIMA forecasting + relative balance loss |
| **Quantization** | INT8 QAT (training-aware) | 4-bit GPTQ (post-training) | Not evaluated |
| **Pruning** | Dynamic token pruning (DTP) | Not evaluated | Implicit via load balancing |
| **Distillation** | AKD (hallucination-aware) | GPT-4→Gemma (task-specific) | Not evaluated |
| **Architecture** | Optimized Transformer | Transformer vs. Mamba (SSM) | MoE with consensus experts |
| **Hardware Validation** | 8 edge devices (Jetson, Coral, RPi) | A100 + Jetson Orin | Single A100 only |
| **Energy Measurement** | Yes (mJ, WCET) | No (inferred) | No |
| **Scale** | BERT-base (~110M) | Up to Llama-3-8B | Switch-base-8/16/32 |
| **Training Overhead** | High (multi-objective) | Low (post-training) / Med (KD) | Low (ARIMA is lightweight) |
| **Open Code** | Yes (GitHub) | Not specified | Not specified |

---

## Research Gaps & Future Directions (Cross-Paper)

1. **Quantized DynamicMoE:** Apply [2]'s 4-bit GPTQ to [3]'s Switch Transformer with expert-specific bit allocation guided by ARIMA load predictions.
2. **Hallucination-Aware MoE Routing:** Integrate [1]'s HAAM attention entropy signals into [3]'s router to bias away from experts producing high-uncertainty outputs.
3. **Pruned + Quantized + Distilled Pipeline:** Combine all three: [3] for training-efficient MoE, [1] for inference pruning, [2] for quantization/distillation — a full-stack efficiency pipeline.
4. **Distributed DynamicMoE:** Extend [3]'s single-GPU dynamic capacity to expert-parallel distributed training (inter-device load balancing + intra-device ARIMA).
5. **Edge Deployment of MoE:** Deploy [3]'s DynamicMoE on [1]'s hardware targets (Jetson, Coral) with [2]'s quantization — measure real energy/latency.
6. **Consensus Expert as Reliability Anchor:** Formalize the consensus expert's role as a cross-layer hallucination detector (leveraging its global token view).
7. **Heterogeneous Expert Architectures:** Move beyond homogeneous experts in [3] — mix Transformer experts with Mamba experts ([2]'s finding: Mamba excels at streaming) guided by task-type routing.

---

*This synthesis is complete. All three papers in the folder have been processed and integrated.*