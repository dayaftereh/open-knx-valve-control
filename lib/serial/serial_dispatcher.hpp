#ifndef SERIAL_DISPATCHER_HPP
#define SERIAL_DISPATCHER_HPP

#include <Print.h>
#include <Stream.h>
#include <common.hpp>

#include <serial_message.hpp>
#include <serial_dispatch_handler.hpp>
#include <serial_unit_type_message.hpp>

// check if SERIAL_BUFFER_SIZE is already defined
#ifndef SERIAL_BUFFER_SIZE
#define SERIAL_BUFFER_SIZE 128
#endif

class SerialDispatcher : public Print
{
public:
	[[nodiscard]] bool setup(Stream &stream, SerialDispatchHandler serialDispatchHandler, UnitType unitType, uint8_t version)
	{
		// set the stream
		this->stream = &stream;
		this->version = version;
		// set the unit type
		this->unitType = unitType;
		// set the dispatcher
		this->serialDispatchHandler = serialDispatchHandler;

		// make the buffer to serial message
		this->serialMessage = (SerialMessage *)this->buffer;

		this->reset();

		return true;
	}

	void update()
	{

		// check for data available
		if (this->stream->available() < 1)
		{

			return;
		}

		// check if a message is in receiving
		if (this->isReceivingMessageData())
		{

			// read the message body to buffer
			this->readMessageToBuffer();
			return;
		}

		// try to read the next message

		this->readNextMessage();
	}

	[[nodiscard]] size_t writeMessage(SerialMessage *message, size_t size)
	{
		// make the message to a buffer
		uint8_t *data = (uint8_t *)(message);

		// write the message to stream
		size_t writtenBytes = this->writeByteMessage(data, size);

		return writtenBytes;
	}

	[[nodiscard]] size_t writeByteMessage(uint8_t *data, size_t size)
	{
		// write the message to the stream
		size_t writtenBytes = this->stream->write(data, size);
		// flush the stream buffer
		this->stream->flush();

		return writtenBytes;
	}

	// overwrite from print
	[[nodiscard]] size_t write(uint8_t c)
	{
		// forward the byte to serial
		return this->stream->write(c);
	}

	[[nodiscard]] size_t write(const uint8_t *buffer, size_t size)
	{
		SerialMessage message;
		// set the message type to print
		message.type = SerialMessageType::Print;
		// set the size of the print message
		message.length = (uint16_t)size;

		// make the message header to a buffer
		uint8_t *header = (uint8_t *)(&message);
		// write the header of the message to the stream
		size_t writtenHeader = this->stream->write(header, sizeof(message));

		// write the print message to the stream
		size_t writtenContent = this->stream->write(buffer, size);
		// flush the stream buffer
		this->stream->flush();

		return writtenHeader + writtenContent;
	}

private:
	void reset()
	{
		// set the buffer index to the offset length from serial message
		this->bufferIndex = 0;
		memset(this->buffer, 0, sizeof(this->buffer));

		this->serialMessage->length = 0;
		this->serialMessage->type = SerialMessageType::Unknown;
	}

	void readNextMessage()
	{
		// get the size of the message
		size_t messageSize = sizeof(SerialMessage);
		if (size_t(this->stream->available()) < messageSize)
		{
			return;
		}

		// make the serial message to buffer
		uint8_t *buffer = (uint8_t *)(this->serialMessage);
		// read the serial message from buffer
		this->stream->readBytes(buffer, messageSize);

		// check if the message with zero payload
		if (this->serialMessage->length > 1)
		{
			return;
		}

		// execute read completed message
		this->readMessageToBuffer();
	}

	void readMessageToBuffer()
	{

		// read each byte from stream
		while (this->stream->available() > 0 && this->bufferIndex < this->serialMessage->length)
		{
			// read the next byte
			uint8_t b = this->stream->read();
			// get the next buffer index
			size_t index = (this->bufferIndex++) + sizeof(SerialMessage);
			// set the read byte to buffer
			this->buffer[index] = b;
		}

		// check if full message received
		if (this->bufferIndex < this->serialMessage->length)
		{
			return;
		}

		// notify about received serial message
		this->onSerialMessage();
		// reset the buffer for the next message
		this->reset();
	}

	void onSerialMessage()
	{
		switch (this->serialMessage->type)
		{
		case SerialMessageType::UnitType:
			return this->onRequestUnitType();

		default:;
		}

		// check if a dispatch handler given
		if (this->serialDispatchHandler == NULL)
		{
			return;
		}

		// make the serial-message
		SerialMessage *message = (SerialMessage *)this->serialMessage;
		// notify the handler about message
		this->serialDispatchHandler(message);
	}

	[[nodiscard]] bool isReceivingMessageData()
	{
		return this->serialMessage->type != SerialMessageType::Unknown;
	}

	void onRequestUnitType()
	{
		SerialUnitTypeMessage message;
		// calculate the length of the payload
		message.length = sizeof(SerialUnitTypeMessage) - sizeof(SerialMessage);
		message.version = this->version;
		message.unitType = this->unitType;
		message.type = SerialMessageType::UnitType;

		SerialMessage *m = (SerialMessage *)&message;
		this->writeMessage(m, sizeof(message));
	}

	uint8_t version;

	UnitType unitType;
	SerialMessage *serialMessage;

	size_t bufferIndex;
	uint8_t buffer[SERIAL_BUFFER_SIZE];

	Stream *stream;
	SerialDispatchHandler serialDispatchHandler;
};

#endif // SERIAL_DISPATCHER_HPP
