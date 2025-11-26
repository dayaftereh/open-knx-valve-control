#ifndef SERIAL_DISPATCH_HANDLER_HPP
#define SERIAL_DISPATCH_HANDLER_HPP

#include "common.hpp"
#include <serial_message.hpp>

using SerialDispatchHandler = void (*)(SerialMessage *message);

#endif // SERIAL_DISPATCH_HANDLER_HPP
