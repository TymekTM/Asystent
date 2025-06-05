# Onboarding Experience

The Gaja application now features a streamlined onboarding experience to help new users get started quickly and configure the system to their needs.

## Overview

When you launch Gaja for the first time, the onboarding wizard automatically opens in your default web browser. This interactive process guides you through the essential setup steps to customize your AI assistant.

## Onboarding Steps

### 1. Welcome Introduction

- Welcome screen with basic information about Gaja
- Overview of the setup process
- Getting started guidance
- Navigation instructions

### 2. Gaja Personalization

- Set your AI assistant's name (default: "Gaja")
- Configure the wake word for voice activation (default: "gaja")
- Select your primary language for interactions
- Customize Gaja's behavior

### 3. Voice Configuration

- Select your microphone device from available audio inputs
- Test microphone functionality
- Configure voice recognition sensitivity
- Enable or disable automatic speech recognition

### 4. AI Provider Selection

Choose your preferred AI provider from the available options:

- **OpenAI**: Configure GPT models with API key
- **Anthropic**: Set up Claude models with API key
- **DeepSeek**: Configure DeepSeek models with API key
- **Local**: Connect to locally running models via Ollama or LM Studio

### 5. Complete Setup

- Save all configurations
- Apply settings to the system
- Mark onboarding as complete
- Launch the main application interface

## Resuming Onboarding

If the onboarding process is interrupted, your progress is saved automatically. The next time you launch the application, you can continue where you left off.

## Manual Configuration

If you prefer to skip the onboarding process or need to reconfigure later:

1. Access the settings page in the web UI
2. Update individual configuration parameters
3. Save your changes

## Troubleshooting

If you encounter issues during onboarding:

- **Browser doesn't open automatically**: Navigate to http://localhost:5000/onboarding manually
- **Configuration not saving**: Check folder permissions and disk space
- **Model connection issues**: Verify your API keys and network connection
- **Audio device problems**: Ensure your microphone is properly connected and not in use by another application
