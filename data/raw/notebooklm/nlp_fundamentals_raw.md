## NLP Sub-Competency 1: Token

### 1. Question 1

What is the fundamental role of tokenisation in an NLP pipeline, and how does the model handle these tokens numerically?

**Answer:**

Tokenisation is the initial step that breaks a continuous block of raw text down into smaller, manageable units called tokens (such as words, parts of words, or characters)1. Once the text is split, a dictionary is created to represent these tokens as numerical indices so they can be processed by a neural network1.

### 2. Question 2

Why are special boundary tokens like [BOS] (Beginning of Sequence) and [EOS] (End of Sequence) introduced during text tokenisation?

**Answer:**

In Transformer models, special tokens are added to mark sequence boundaries1. [BOS] indicates the start of a text block, while [EOS] marks the end1. This is conceptually critical for sequence-to-sequence tasks (like language translation or generation) because it explicitly signals where the input begins and where the generator should stop creating output1.

### 3. Question 3

From a computational efficiency standpoint, why do sequential models like Recurrent Neural Networks (RNNs) suffer from processing bottlenecks, and how do Transformers bypass this?

**Answer:**

RNNs are sequential, meaning they process tokens step-by-step and rely on a feedback loop from the previous token to compute the current state2. This makes processing large documents highly time-consuming because computations cannot be parallelised2. Transformers process all tokens in a sequence simultaneously (in parallel), which eliminates sequential recurrence and drastically improves training speed2.

### 4. Question 4

When designing an NLP system for long-horizon tasks, what are the trade-offs of choosing a very small vocabulary size versus a very large vocabulary size during tokenisation?

**Answer:**

- A small vocabulary size forces the tokeniser to break words into highly fragmented, smaller sub-word units2. This keeps the model parameter footprint small but increases the overall sequence length (more tokens per sentence), leading to higher computational costs in self-attention12.

- A large vocabulary size keeps sequence lengths shorter (fewer tokens) but drastically increases the size of the final output layer (softmax), which increases memory usage and model parameter overhead12.

### 5. Question 5

Why is character-level tokenisation generally less efficient than sub-word tokenisation (like Byte-Pair Encoding) for large documents in Transformer architectures?

**Answer:**

Character-level tokenisation splits text into individual characters, which exponentially increases the sequence length (the number of tokens) for a given document2. Because self-attention mechanisms scale quadratically with sequence length, this massive increase in tokens leads to excessive computational overhead and memory blowouts1. Sub-word tokenisation keeps sequences significantly shorter while still preventing out-of-vocabulary errors2.

## NLP Sub-Competency 2: Embedding

### 1. Question 1

What is the mathematical limitation of One-Hot Encoding in capturing semantic relationships between words, and how do dense Word Embeddings resolve this?

**Answer:**

In One-Hot Encoding, words are represented as sparse, high-dimensional vectors2. Because each word has a "1" in a unique position and "0" elsewhere, the Euclidean distance between any two distinct words is always constant (e.g., $\sqrt{2}$)2. This means One-Hot Encoding cannot measure semantic similarity or context; "cat" and "car" are mathematically as distant as "cat" and "dog"2. Dense Word Embeddings compress words into continuous, lower-dimensional vectors where semantically similar words are mapped closer together2.

### 2. Question 2

How do the two primary training architectures of Word2Vec—Continuous Bag of Words (CBOW) and Skip-gram—differ in their learning objectives?

**Answer:**

- CBOW predicts a single target word from its surrounding context words2.

- Skip-gram does the inverse: it takes a single target word and predicts the surrounding context words within a defined window2. Skip-gram typically learns better representations for rare words because it generates multiple training pairs for each occurrence2.

### 3. Question 3

Explain the conceptual difference between Word2Vec and GloVe (Global Vectors) in how they utilise corpus statistics to build word vectors.

**Answer:**

- Word2Vec is a predictive model that slides a local context window across a corpus to learn word associations sequentially2.

- GloVe is a count-based model that constructs a massive global co-occurrence matrix containing statistical word frequencies across the entire dataset at once, then performs matrix factorisation to optimize the vectors2. GloVe is conceptually superior at capturing global, corpus-wide statistical relationships2.

### 4. Question 4

What is the difference between a static embedding (like Word2Vec) and a dynamic contextual representation (like in a Transformer)?

**Answer:**

Static embeddings assign a single, fixed vector to a word in their vocabulary, completely ignoring context during inference (the word "bank" has the same vector in "river bank" and "investment bank")12. Transformers use self-attention to dynamically adjust a word's vector representation at runtime based on the actual surrounding tokens in the sentence, yielding distinct context-aware embeddings12.

### 5. Question 5

Since self-attention in Transformers has no recursive loop to keep track of sequential order, how is token order preserved, and what is the difference between Additive Positional Encoding and Rotary Position Encoding (RoPE)?

**Answer:**

Positional encodings inject sequential order directly into the token representations1.

- Additive Positional Encoding uses trigonometric functions to compute a static position vector, which is mathematically added directly to the word embedding vector1.

- Rotary Position Encoding (RoPE) operates dynamically by rotating pairs of values within the word vector by specific degrees determined by the token's position index (e.g., tilting vectors like coordinates on a graph), preserving relative distances between tokens much more effectively1.

## NLP Sub-Competency 3: Transformer Architecture

### 1. Question 1

Using the analogy of a search engine, explain the conceptual roles of the Query (Q), Key (K), and Value (V) vectors in the self-attention mechanism.

**Answer:**

- **Query (Q):** Represents the search term or what a specific token is actively "asking" for to understand its surrounding context1.

- **Key (K):** Represents the metadata or index headers of other words in the sentence, advertising what kind of information they can offer1.

- **Value (V):** Represents the actual content or semantic information carried by each word, which gets extracted and aggregated if its Key is highly relevant to the Query1.

### 2. Question 2

Outline the step-by-step mathematical flow of how the self-attention mechanism computes a context-aware vector for a word in the sentence "Attention is cool".

**Answer:**

1. The token vectors are passed through learned linear layers to produce $Q$, $K$, and $V$ vectors1.

2. Calculate raw attention scores by taking the dot product of "Attention's" query vector ($Q_0$) with the key vectors of all words ($K_0, K_1, K_2$)1.

3. Pass the raw scores through a softmax function to scale them into normalized weights between 0 and 1 that sum to 11.

4. Multiply these weights by the respective value vectors ($V_0, V_1, V_2$) and sum them up to produce a final, context-mixed vector for "Attention"1.

### 3. Question 3

What is the structural difference between the primary objective of a Transformer's Encoder and its Decoder?

**Answer:**

The Encoder takes an entire input sequence and processes it simultaneously to transform a block of text into a sequence of context-aware vectors1. The Decoder's role is autoregressive generation; it uses the representations created by the encoder to generate an output sequence (like a translation) one token at a time by predicting the next most likely word1.

### 4. Question 4

What is Masked Multi-Head Self-Attention, and why is it functionally critical during the parallel training of generative decoders?

**Answer:**

In generative decoders, masking modifies the attention matrix by setting the raw scores of "future" tokens to negative infinity ($-\infty$), which mathematically zeroes out their weights after softmax1. During parallel training, the entire target sequence is fed to the model at once1. Without masking, the model would cheat by looking ahead at the future words it is learning to predict; masking forces the model to predict the next word using only past context1.

### 5. Question 5

What is Multi-Head Self-Attention (MHSA), and why is it conceptually superior to having a single, large self-attention head?

**Answer:**

Instead of computing self-attention once, MHSA splits the queries, keys, and values into multiple lower-dimensional projection subspaces (e.g., heads $Q_0$-$Q_6$) and computes attention on each head in parallel1. This is superior because it allows the model to jointly attend to different types of relationships at different positions at the same time (e.g., one head can focus on grammatical agreement while another head focuses on thematic concepts)1. The outputs are then concatenated and combined1.
