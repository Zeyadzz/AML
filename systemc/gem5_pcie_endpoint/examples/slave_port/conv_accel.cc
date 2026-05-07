#include "conv_accel.h"
#include <cstring>
#include <iostream>

using namespace sc_core;
using namespace tlm;

ConvAccel::ConvAccel(sc_module_name name) : sc_module(name),
    target_socket("target_socket"),
    peq(this, &ConvAccel::peq_cb),
    status_reg(1)
{
    std::memset(sram, 0, sizeof(sram));

    target_socket.register_nb_transport_fw(this, &ConvAccel::nb_transport_fw);

    SC_METHOD(compute_process);
    sensitive << compute_done_event;
    dont_initialize();
}

tlm_sync_enum ConvAccel::nb_transport_fw(tlm_generic_payload& trans, tlm_phase& phase, sc_time& t) {
    // Always return TLM_ACCEPTED immediately; defer processing to the PEQ
    peq.notify(trans, phase, t);
    return TLM_ACCEPTED;
}

void ConvAccel::peq_cb(tlm_generic_payload& trans, const tlm_phase& phase) {
    if (phase == BEGIN_REQ) {
        uint64_t addr = trans.get_address();
        unsigned char* data = trans.get_data_ptr();
        unsigned int len = trans.get_data_length();
        tlm_command cmd = trans.get_command();

        if (addr >= 0x40000000 && addr <= 0x40000FFF) {
            uint64_t offset = addr - 0x40000000;
            if (offset + len <= sizeof(sram)) {
                if (cmd == TLM_READ_COMMAND) {
                    std::memcpy(data, &sram[offset], len);
                } else if (cmd == TLM_WRITE_COMMAND) {
                    std::memcpy(&sram[offset], data, len);
                }
                trans.set_response_status(TLM_OK_RESPONSE);
            } else {
                trans.set_response_status(TLM_ADDRESS_ERROR_RESPONSE);
            }
        } 
        else if (addr == 0x40001000) { // Control Register
            if (cmd == TLM_WRITE_COMMAND && len == sizeof(uint32_t)) {
                uint32_t val;
                std::memcpy(&val, data, sizeof(uint32_t));
                
                if (val == 1 && status_reg == 1) { // Start computation
                    status_reg = 0; // Set to computing
                    
                    // Delay calc: (matrix_size * operations_per_element) * clock_period
                    // e.g. matrix_size = 64, operations_per_element = 2, clock_period = 10 ns
                    sc_time delay(64 * 2 * 10, SC_NS);
                    compute_done_event.notify(delay);
                }
                trans.set_response_status(TLM_OK_RESPONSE);
            } else {
                trans.set_response_status(TLM_COMMAND_ERROR_RESPONSE);
            }
        }
        else if (addr == 0x40001004) { // Status Register
            if (cmd == TLM_READ_COMMAND && len == sizeof(uint32_t)) {
                std::memcpy(data, &status_reg, sizeof(uint32_t));
                trans.set_response_status(TLM_OK_RESPONSE);
            } else {
                trans.set_response_status(TLM_COMMAND_ERROR_RESPONSE);
            }
        } else {
            trans.set_response_status(TLM_ADDRESS_ERROR_RESPONSE);
        }

        // Send END_REQ and BEGIN_RESP (combining for efficiency to complete the response)
        tlm_phase resp_phase = BEGIN_RESP;
        sc_time resp_delay = SC_ZERO_TIME;
        target_socket->nb_transport_bw(trans, resp_phase, resp_delay);
    } 
    else if (phase == END_RESP) {
        // Master acknowledged the transaction completion. No further action needed here.
    }
}

void ConvAccel::compute_process() {
    // Apply dummy math transformation to the local SRAM
    for (size_t i = 0; i < sizeof(sram); i++) {
        sram[i] = sram[i] ^ 0xAA; // Simple dummy manipulation
    }

    // Set Status back to 1 (idle/done)
    status_reg = 1;
}
