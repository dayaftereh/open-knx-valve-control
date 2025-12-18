#ifndef SERIAL_MESSAGE_DISPATCHER_HPP
#define SERIAL_MESSAGE_DISPATCHER_HPP

#include <config_manager.hpp>
#include <serial_dispatcher.hpp>

#include "config.hpp"
#include "temperatures.hpp"

#include "serial-messages/serial_config_message.hpp"
#include "serial-messages/serial_status_message.hpp"

class SerialMessageDispatcher
{
public:
    [[nodiscard]] bool setup(Temperatures &temperatures, SerialDispatcher &serialDispatcher, ConfigManager<Config> &configManager, Print &print);

    void onMessage(SerialMessage *message);

private:
    void handleStatus();
    void handleRequestConfig();
    void handleConfig(SerialConfigMessage *message);

    Print *print;
    Temperatures *temperatures;
    SerialDispatcher *serialDispatcher;
    ConfigManager<Config> *configManager;
};

#endif // SERIAL_MESSAGE_DISPATCHER_HPP