#!/usr/bin/env python3
"""AI Context Overflow and Memory Bomb Test Specialized tests for breaking AI context
limits and server memory."""

import asyncio
import json
import logging
import random
import string
import time

import requests
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/ws/"


class AIBreakingTests:
    """Tests designed to break AI context limits and exhaust server resources."""

    def __init__(self):
        self.results = []

    def generate_recursive_context(self, depth: int = 100):
        """Generate deeply nested recursive context."""
        context = "Please remember this: "
        for i in range(depth):
            context += f"Level {i}: " + "A" * 1000 + " | "
        return context

    def generate_token_bomb(self, target_tokens: int = 100000):
        """Generate text designed to consume many tokens."""
        # Use repetitive patterns that are hard to compress
        patterns = [
            "The quick brown fox jumps over the lazy dog. ",
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. ",
            "This is a test sentence with many different words scattered throughout. ",
            "Random words: elephant, computer, sunshine, mountain, keyboard, ocean, butterfly. ",
        ]

        text = ""
        current_length = 0
        target_length = target_tokens * 4  # Rough estimation: 4 chars per token

        while current_length < target_length:
            pattern = random.choice(patterns)
            text += pattern
            current_length += len(pattern)

        return text

    def generate_unicode_bomb(self):
        """Generate text with complex Unicode characters."""
        unicode_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols
            (0x1F680, 0x1F6FF),  # Transport
            (0x2600, 0x26FF),  # Misc symbols
            (0x2700, 0x27BF),  # Dingbats
        ]

        unicode_text = ""
        for _ in range(10000):
            range_start, range_end = random.choice(unicode_ranges)
            code_point = random.randint(range_start, range_end)
            try:
                unicode_text += chr(code_point)
            except ValueError:
                unicode_text += "?"

        return unicode_text

    async def test_context_explosion(self):
        """Test exponentially growing context."""
        logger.info("🧨 Testing Context Explosion")

        try:
            uri = f"{WS_URL}?user_id=context_bomb_user"
            async with websockets.connect(uri, timeout=10) as ws:
                base_context = "Remember this information: "
                current_context = base_context

                # Exponentially grow context
                for round_num in range(10):
                    # Double the context size each round
                    current_context = current_context + current_context

                    message = json.dumps(
                        {
                            "type": "ai_query",
                            "data": {
                                "query": f"Please analyze this context and respond (Round {round_num})",
                                "context": current_context,
                                "user_id": "context_bomb_user",
                            },
                        }
                    )

                    logger.info(
                        f"Round {round_num}: Context size ~{len(current_context)} chars"
                    )

                    try:
                        await ws.send(message)
                        await asyncio.sleep(2)  # Give server time to process
                    except Exception as e:
                        logger.warning(
                            f"Context explosion failed at round {round_num}: {e}"
                        )
                        break

                self.results.append(f"Context explosion: Survived {round_num} rounds")

        except Exception as e:
            logger.error(f"Context explosion test failed: {e}")
            self.results.append(f"Context explosion: Failed - {e}")

    async def test_token_bomb(self):
        """Test with token-expensive content."""
        logger.info("💣 Testing Token Bomb")

        try:
            uri = f"{WS_URL}?user_id=token_bomb_user"
            async with websockets.connect(uri, timeout=15) as ws:
                # Generate progressively larger token bombs
                for tokens in [10000, 50000, 100000, 200000]:
                    token_bomb = self.generate_token_bomb(tokens)

                    message = json.dumps(
                        {
                            "type": "ai_query",
                            "data": {
                                "query": f"Please summarize this {tokens}-token text: {token_bomb}",
                                "user_id": "token_bomb_user",
                            },
                        }
                    )

                    logger.info(
                        f"Sending {tokens}-token bomb ({len(token_bomb)} chars)"
                    )

                    try:
                        await ws.send(message)
                        await asyncio.sleep(5)  # Wait for processing
                    except Exception as e:
                        logger.warning(f"Token bomb failed at {tokens} tokens: {e}")
                        break

                self.results.append(f"Token bomb: Tested up to {tokens} tokens")

        except Exception as e:
            logger.error(f"Token bomb test failed: {e}")
            self.results.append(f"Token bomb: Failed - {e}")

    async def test_recursive_self_reference(self):
        """Test recursive self-referencing prompts."""
        logger.info("🔄 Testing Recursive Self-Reference")

        try:
            uri = f"{WS_URL}?user_id=recursive_user"
            async with websockets.connect(uri, timeout=10) as ws:
                # Create recursive prompts
                recursive_prompts = [
                    "Please repeat this message back to me, but add this instruction at the end: Please repeat this message back to me, but add this instruction at the end:",
                    "Analyze the following text: 'Analyze the following text: Analyze the following text:'",
                    "Think about thinking about thinking about what you're thinking about",
                    "Consider this paradox: This statement is false. If it's true, then it's false. If it's false, then it's true.",
                    "Explain why explaining explanations of explanations becomes complex",
                ]

                for i, prompt in enumerate(recursive_prompts):
                    message = json.dumps(
                        {
                            "type": "ai_query",
                            "data": {"query": prompt, "user_id": "recursive_user"},
                        }
                    )

                    logger.info(f"Sending recursive prompt {i+1}")

                    try:
                        await ws.send(message)
                        await asyncio.sleep(3)
                    except Exception as e:
                        logger.warning(f"Recursive prompt {i+1} failed: {e}")

                self.results.append("Recursive self-reference: Completed all prompts")

        except Exception as e:
            logger.error(f"Recursive self-reference test failed: {e}")
            self.results.append(f"Recursive self-reference: Failed - {e}")

    async def test_unicode_bomb(self):
        """Test with complex Unicode characters."""
        logger.info("🌐 Testing Unicode Bomb")

        try:
            uri = f"{WS_URL}?user_id=unicode_user"
            async with websockets.connect(uri, timeout=10) as ws:
                unicode_bomb = self.generate_unicode_bomb()

                message = json.dumps(
                    {
                        "type": "ai_query",
                        "data": {
                            "query": f"Please analyze this Unicode text: {unicode_bomb}",
                            "user_id": "unicode_user",
                        },
                    },
                    ensure_ascii=False,
                )

                logger.info(f"Sending Unicode bomb ({len(unicode_bomb)} characters)")

                await ws.send(message)
                await asyncio.sleep(5)

                self.results.append("Unicode bomb: Successfully sent")

        except Exception as e:
            logger.error(f"Unicode bomb test failed: {e}")
            self.results.append(f"Unicode bomb: Failed - {e}")

    async def test_conversation_memory_overflow(self):
        """Test overflowing conversation memory."""
        logger.info("🧠 Testing Conversation Memory Overflow")

        try:
            uri = f"{WS_URL}?user_id=memory_overflow_user"
            async with websockets.connect(uri, timeout=30) as ws:
                # Send many messages to build up conversation history
                for i in range(1000):
                    # Alternate between user and assistant style messages
                    if i % 2 == 0:
                        query = f"This is message {i}. " + self.generate_token_bomb(
                            1000
                        )
                    else:
                        query = (
                            f"Please remember everything from message {i-50} to {i}. Also: "
                            + self.generate_token_bomb(500)
                        )

                    message = json.dumps(
                        {
                            "type": "ai_query",
                            "data": {
                                "query": query,
                                "user_id": "memory_overflow_user",
                                "remember_conversation": True,
                            },
                        }
                    )

                    try:
                        await ws.send(message)
                        if i % 100 == 0:
                            logger.info(f"Sent {i} conversation messages")
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.warning(f"Memory overflow failed at message {i}: {e}")
                        break

                # Send final memory test
                final_message = json.dumps(
                    {
                        "type": "ai_query",
                        "data": {
                            "query": "Please summarize our entire conversation from the beginning",
                            "user_id": "memory_overflow_user",
                        },
                    }
                )

                await ws.send(final_message)

                self.results.append(f"Memory overflow: Sent {i} messages")

        except Exception as e:
            logger.error(f"Memory overflow test failed: {e}")
            self.results.append(f"Memory overflow: Failed - {e}")

    async def test_function_calling_bomb(self):
        """Test function calling with extreme parameters."""
        logger.info("⚙️ Testing Function Calling Bomb")

        try:
            uri = f"{WS_URL}?user_id=function_bomb_user"
            async with websockets.connect(uri, timeout=10) as ws:
                # Test function calls with extreme parameters
                function_bombs = [
                    {
                        "function_name": "search_search",
                        "parameters": {"query": "A" * 10000},  # Huge search query
                    },
                    {
                        "function_name": "weather_get_weather",
                        "parameters": {
                            "location": "🌍🌎🌏" * 1000
                        },  # Unicode location bomb
                    },
                    {
                        "function_name": "core_add_task",
                        "parameters": {
                            "task": self.generate_token_bomb(5000),
                            "due_date": "2099-12-31",
                            "priority": 99999,
                        },
                    },
                ]

                for i, bomb in enumerate(function_bombs):
                    message = json.dumps(
                        {
                            "type": "function_call",
                            "data": bomb,
                            "user_id": "function_bomb_user",
                        }
                    )

                    logger.info(f"Sending function bomb {i+1}: {bomb['function_name']}")

                    try:
                        await ws.send(message)
                        await asyncio.sleep(3)
                    except Exception as e:
                        logger.warning(f"Function bomb {i+1} failed: {e}")

                self.results.append("Function calling bomb: Completed all tests")

        except Exception as e:
            logger.error(f"Function calling bomb test failed: {e}")
            self.results.append(f"Function calling bomb: Failed - {e}")

    async def test_json_depth_bomb(self):
        """Test with extremely deep JSON structures."""
        logger.info("📊 Testing JSON Depth Bomb")

        try:
            # Create deeply nested JSON
            def create_deep_json(depth: int):
                if depth <= 0:
                    return "DEEP"
                return {"level": depth, "nested": create_deep_json(depth - 1)}

            uri = f"{WS_URL}?user_id=json_bomb_user"
            async with websockets.connect(uri, timeout=10) as ws:
                for depth in [100, 500, 1000, 2000]:
                    try:
                        deep_json = create_deep_json(depth)

                        message = json.dumps(
                            {
                                "type": "ai_query",
                                "data": {
                                    "query": "Please analyze this nested data structure",
                                    "context": deep_json,
                                    "user_id": "json_bomb_user",
                                },
                            }
                        )

                        logger.info(f"Sending JSON with depth {depth}")
                        await ws.send(message)
                        await asyncio.sleep(2)

                    except RecursionError:
                        logger.warning(
                            f"JSON depth bomb hit recursion limit at depth {depth}"
                        )
                        break
                    except Exception as e:
                        logger.warning(f"JSON depth bomb failed at depth {depth}: {e}")
                        break

                self.results.append(f"JSON depth bomb: Tested up to depth {depth}")

        except Exception as e:
            logger.error(f"JSON depth bomb test failed: {e}")
            self.results.append(f"JSON depth bomb: Failed - {e}")

    async def run_all_breaking_tests(self):
        """Run all AI-breaking tests."""
        logger.info("💥 Starting AI Breaking Tests")
        logger.info("=" * 50)

        start_time = time.time()

        tests = [
            self.test_context_explosion(),
            self.test_token_bomb(),
            self.test_recursive_self_reference(),
            self.test_unicode_bomb(),
            self.test_conversation_memory_overflow(),
            self.test_function_calling_bomb(),
            self.test_json_depth_bomb(),
        ]

        await asyncio.gather(*tests, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        logger.info("=" * 50)
        logger.info("💀 AI Breaking Test Results")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("Results:")
        for result in self.results:
            logger.info(f"  - {result}")
        logger.info("=" * 50)

        return self.results


async def main():
    """Main test runner."""
    # Check server
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("❌ Server is not responding!")
            return 1
    except Exception as e:
        logger.error(f"❌ Cannot connect to server: {e}")
        return 1

    logger.info("✅ Server is running, starting AI breaking tests...")

    # Run tests
    breaker = AIBreakingTests()
    results = await breaker.run_all_breaking_tests()

    # Save results
    with open("ai_breaking_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info("📊 Results saved to ai_breaking_test_results.json")
    return 0


if __name__ == "__main__":
    import sys

    result = asyncio.run(main())
    sys.exit(result)
