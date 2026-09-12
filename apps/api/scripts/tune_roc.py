import json
import numpy as np

def sigmoid(x, k, x0):
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))

def simulate_ensemble(file_chunks, w_pdi, w_tremor, w_formant, safe_thresh, pdi_x0, tremor_x0, disagree_thresh=0.50):
    safe_cnt = 0
    synth_cnt = 0
    uncert_cnt = 0
    formant_history = []
    
    for c in file_chunks:
        # Formant memory
        curr_f = c['formant_raw']
        if curr_f != 0.5:
            formant_history.append(curr_f)
        if len(formant_history) > 3:
            formant_history.pop(0)
        f_human = float(sum(formant_history) / len(formant_history)) if formant_history else 0.5
        
        # Scaling
        p_human = sigmoid(c['pdi_raw'], 15.0, pdi_x0)
        t_human = sigmoid(c['tremor_raw'], 30.0, tremor_x0)
        
        ens = w_pdi * p_human + w_tremor * t_human + w_formant * f_human
        disagree = max(p_human, t_human, f_human) - min(p_human, t_human, f_human)
        
        if disagree > disagree_thresh:
            uncert_cnt += 1
        elif ens >= (1.0 - safe_thresh):
            safe_cnt += 1
        elif ens <= (1.0 - 0.40): # synthetic threshold fixed for now
            synth_cnt += 1
        else:
            uncert_cnt += 1
            
    return safe_cnt, synth_cnt, uncert_cnt

def main():
    with open(r"d:\PhaseGuard\apps\api\dataset_v2\raw_features.json", "r") as f:
        data = json.load(f)
        
    # Group by file
    files = {}
    for row in data:
        files.setdefault(row['file'], []).append(row)
        
    premium_ai = ["ElevenLabs_2026-09-01T15_58_06_Kanika - Warm, Expressive and Natural_pvc_sp100_s50_sb75_se0_m2.mp3", "hindi_ai_voice.mp3"]
    crude_ai = ["scam_bank_fraud.mp3", "scam_irs.mp3", "scam_kidnapping.mp3", "scam_tech_support.mp3", "new_ai_voice.mp3"]
    noisy_human = ["originalvo-medieval-gamer-voice-darkness-hunts-us-what-youx27ve-learned-stay-226596.mp3"]
    clean_human = [f for f in files.keys() if f not in premium_ai and f not in crude_ai and f not in noisy_human]
    
    # Evaluate optimal config
    w_pdi = 0.70
    w_rest = 0.15
    pdi_x0 = 0.75
    tremor_x0 = 0.10
    safe_thresh = 0.20
    
    print(f"--- Full Breakdown for Optimal Config ---")
    print(f"W_PDI={w_pdi}, W_TREMOR={w_rest}, W_FORMANT={w_rest}")
    print(f"PDI_X0={pdi_x0}, TREMOR_X0={tremor_x0}, SAFE_THRESH={safe_thresh}\n")
    
    for fname, chunks in files.items():
        s, sy, u = simulate_ensemble(chunks, w_pdi, w_rest, w_rest, safe_thresh, pdi_x0, tremor_x0)
        
        category = "Clean Human"
        if fname in premium_ai: category = "Premium AI"
        elif fname in crude_ai: category = "Crude AI"
        elif fname in noisy_human: category = "Noisy Human"
            
        print(f"[{category}] {fname}:")
        print(f"  SAFE: {s}, SYNTHETIC: {sy}, UNCERTAIN: {u}\n")

if __name__ == "__main__":
    main()
