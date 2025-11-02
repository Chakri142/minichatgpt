from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# --- 1. Load Model and Tokenizer ---
# This will download the model (once) and save it.
print("Loading model... This might take a few minutes.")
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")
print("Model loaded!")

# --- 2. Initialize Chat History ---
# We will store the conversation history as a tensor of token IDs.
chat_history_ids = None

# --- 3. Start the Chat Loop ---
print("Chatbot is ready! Type 'exit' to end the conversation.")
while True:
    # Get user input
    user_input = input("You: ")

    if user_input.lower() == 'exit':
        break

    # --- 4. Prepare Input for the Model ---
    # A. Encode the new user input
    new_user_input_ids = tokenizer.encode(user_input + tokenizer.eos_token, return_tensors='pt')

    # B. Append the new input to the history
    if chat_history_ids is not None:
        # If we have history, concatenate it with the new input
        bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1)
    else:
        # If this is the first message, just use the new input
        bot_input_ids = new_user_input_ids

    # --- 5. Generate a Response ---
    # This is where the magic happens!
    # We limit the response length and use sampling for more natural answers.
    chat_history_ids = model.generate(
        bot_input_ids,
        max_length=1000,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True, # Enables more "creative" responses
        top_k=50,       # Considers the top 50 most likely next words
        top_p=0.95,     # Uses nucleus sampling
        temperature=0.7 # Makes the output less predictable (lower = more deterministic)
    )

    # --- 6. Decode and Print the Response ---
    # We decode the *entire* history, then find the last response.
    full_response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
    print(f"Bot: {full_response}")