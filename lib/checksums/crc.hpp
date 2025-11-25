#ifndef CRC_HPP
#define CRC_HPP

#include <stddef.h>
#include <stdint.h>

/**
 * @brief the options for the crc-calculation
 *
 * @tparam T crc-datatype uint8_t, uint16_t, ...
 */
template <typename T>
struct __attribute__((packed)) CrcOptions
{
    using Type_t = T;

    /**
     * @brief construct a CrcOptions objects
     *
     */
    constexpr CrcOptions(T checkT, T polyT, T initT)
        : check(checkT), poly(polyT), init(initT)
    {

    }

    T check;
    T poly;
    T init;
};

/**
 * @brief CrcOptions for the common crc8 algorithm
 *
 */
static constexpr CrcOptions<uint8_t> Crc8Options(0x80, 0x31, 0xFF); //fixed crc value to minimize colisions

/**
 * @brief calculate crc value
 *
 * @tparam T the target datatype (see CrcOptions)
 * @param data data pointer of @tparam T
 * @param elementCount element-count (not bytecount)
 * @param options crc-options
 * @return constexpr T calculated crc-value (or 0 on error)
 */
template <typename T>
[[nodiscard]] constexpr T calculateCrc(const T* data, uint16_t elementCount, const CrcOptions<T>& options = Crc8Options)
{
    //return 0 if data is nullptr or the elementcount is invalid
    if (data == nullptr || elementCount < 1)
    {
        return 0;
    }

    T crc = options.init;

    for (decltype(elementCount) i = 0; i < elementCount; i++)
    {
        crc ^= data[i];

        for (uint8_t j = 0; j < 8; j++)
        {
            if ((crc & options.check) != 0)
            {
                crc = T((crc << 1) ^ options.poly);
            }

            else
            {
                crc <<= 1;
            }
        }
    }

    return crc;
}

#if 0
template <auto Data, auto Options>
[[nodiscard]] constexpr auto calculateCrc()
{
    using T = typename decltype(Options)::Type_t;

    T crc = Options.init;

    for (size_t i = 0; i < Data.size(); i++)
    {
        crc ^= Data[i];

        for (uint8_t j = 0; j < 8; j++)
        {
            if ((crc & Options.check) != 0)
            {
                crc = T((crc << 1) ^ Options.poly);
            }

            else
            {
                crc <<= 1;
            }
        }
    }

    return crc;
}
#endif

/**
 * @brief check if a crc value is valid
 *
 * @tparam T the target datatype (see CrcOptions)
 * @param targetCrc the value to checked against
 * @param data data pointer of @tparam T
 * @param elementCount element-count (not bytecount)
 * @param options crc-options
 * @return true crc @param targetCrc is valid
 * @return false crc is invalid
 */
template <typename T>
[[nodiscard]] constexpr bool checkCrc(T targetCrc, const T* data, uint16_t elementCount, const CrcOptions<T>& options = Crc8Options)
{
    //return 0 if data is nullptr or the elementcount is invalid
    if (data == nullptr || elementCount < 1)
    {
        return false;
    }

    return (calculateCrc(data, elementCount, options) == targetCrc);
}


#endif