#ifndef CONV_ACCEL_H
#define CONV_ACCEL_H

#include <systemc>
#include <tlm>
#include <tlm_utils/simple_target_socket.h>
#include <tlm_utils/peq_with_cb_and_phase.h>

class ConvAccel : public sc_core::sc_module {
public:
    tlm_utils::simple_target_socket<ConvAccel> target_socket;

    SC_HAS_PROCESS(ConvAccel);
    ConvAccel(sc_core::sc_module_name name);

private:
    tlm::tlm_sync_enum nb_transport_fw(tlm::tlm_generic_payload& trans, tlm::tlm_phase& phase, sc_core::sc_time& t);
    void peq_cb(tlm::tlm_generic_payload& trans, const tlm::tlm_phase& phase);
    void compute_process();

    tlm_utils::peq_with_cb_and_phase<ConvAccel> peq;

    sc_core::sc_event compute_done_event;

    // Memory map logic
    uint8_t sram[0x1000]; // 0x40000000 - 0x40000FFF
    uint32_t status_reg;  // 0x40001004 (1 = idle, 0 = computing)
};

#endif // CONV_ACCEL_H
