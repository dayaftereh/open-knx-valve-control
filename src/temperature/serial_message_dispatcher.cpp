#include "serial_message_dispatcher.hpp"

[[nodiscard]] bool SerialMessageDispatcher::setup(Temperatures &temperatures, SerialDispatcher &serialDispatcher, ConfigManager<Config> &configManager, Print &print)
{
    this->print = &print;
    this->temperatures = &temperatures;
    this->configManager = &configManager;
    this->serialDispatcher = &serialDispatcher;

    return true;
}

void SerialMessageDispatcher::onMessage(SerialMessage *message)
{
    switch (message->type)
    {
    case SerialMessageType::Status:
        this->handleStatus();
        return;
    case SerialMessageType::Config:
        this->handleConfig((SerialConfigMessage *)message);
        return;
    case SerialMessageType::RequestConfig:
        this->handleRequestConfig();
        return;
    }
}

void SerialMessageDispatcher::handleStatus()
{
    SerialStatusMessage message;

    message.length = sizeof(message) - sizeof(SerialMessage);
    message.type = SerialMessageType::Status;

    this->serialDispatcher->writeMessage(&message, sizeof(message));
}

void SerialMessageDispatcher::handleConfig(SerialConfigMessage *message)
{
    // update the config
    this->configManager->setConfig(message->config);
    // save the config
    this->configManager->save();
}

void SerialMessageDispatcher::handleRequestConfig()
{
    // make the message header for the config
    SerialConfigMessage message;
    message.length = sizeof(message) - sizeof(SerialMessage);
    message.type = SerialMessageType::Config;

    // get the current config
    Config *config = this->configManager->getConfig();
    // insert the config
    message.config = *config;

    // writ ethe message header
    this->serialDispatcher->writeMessage(&message, sizeof(message));
}