"""Experimental GPT-2-era text classifier. No remote inference."""
from functools import lru_cache
from threading import Lock
from .text_assets import files

TEXT_LOCK=Lock()
class TextError(ValueError):
    pass

@lru_cache(maxsize=1)
def load_text_model():
    import torch
    from transformers import RobertaConfig,RobertaForSequenceClassification,RobertaTokenizer
    torch.set_num_threads(2)
    folder=files()
    model=RobertaForSequenceClassification(RobertaConfig.from_json_file(folder/'config.json'))
    data=torch.load(folder/'detector-base.pt',map_location='cpu',weights_only=True)
    state=data['model_state_dict']
    # Older Transformers stored these constant buffers as checkpoint weights.
    state={k:v for k,v in state.items() if k not in {'roberta.embeddings.position_ids','roberta.embeddings.token_type_ids','roberta.pooler.dense.weight','roberta.pooler.dense.bias'}}
    model.load_state_dict(state,strict=True)
    tokenizer=RobertaTokenizer(vocab_file=str(folder/'vocab.json'),merges_file=str(folder/'merges.txt'))
    return model.eval(),tokenizer

def analyze_text(text):
    import torch
    if not isinstance(text,str) or len(text.split())<50:
        raise TextError('Paste at least 50 words of English prose for an experimental assessment.')
    if len(text)>20000:
        raise TextError('Maximum input length is 20,000 characters.')
    with TEXT_LOCK:
        model,tokenizer=load_text_model()
        encoded=tokenizer.encode(text,add_special_tokens=False)
        truncated=len(encoded)>510
        tokens=[tokenizer.bos_token_id]+encoded[:510]+[tokenizer.eos_token_id]
        inputs=torch.tensor([tokens])
        with torch.inference_mode():
            logits=model(inputs,attention_mask=torch.ones_like(inputs)).logits[0]
            ai_score=float(torch.softmax(logits,dim=-1)[0])
    is_ai=ai_score>=0.5
    return {'model':'OpenAI GPT-2 output detector (RoBERTa-base)',
            'is_ai':is_ai,'verdict':'AI-like text' if is_ai else 'Human-like text',
            'model_ai_score':ai_score,'tokens_analyzed':len(tokens)-2,
            'analysis_limit_reached':truncated,
            'notice':'Experimental GPT-2-era detector. Not validated for modern ChatGPT or other current models. Can misclassify human writing. Score is not proof or calibrated probability.'}
