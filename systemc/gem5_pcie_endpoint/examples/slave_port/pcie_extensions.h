#ifndef PCIE_EXTENSIONS_H
#define PCIE_EXTENSIONS_H

#include <tlm>
#include <cstdint>

class PCIeFlitExtension : public tlm::tlm_extension<PCIeFlitExtension> {
public:
    uint64_t flit_id;
    bool is_ack;
    bool is_nak;
    uint32_t payload_size;
    bool is_tail;

    PCIeFlitExtension()
        : flit_id(0), is_ack(false), is_nak(false), payload_size(0), is_tail(false) {}

    virtual tlm_extension_base* clone() const override {
        PCIeFlitExtension* ext = new PCIeFlitExtension();
        ext->flit_id = this->flit_id;
        ext->is_ack = this->is_ack;
        ext->is_nak = this->is_nak;
        ext->payload_size = this->payload_size;
        ext->is_tail = this->is_tail;
        return ext;
    }

    virtual void copy_from(tlm_extension_base const& ext) override {
        const PCIeFlitExtension* flit_ext = static_cast<const PCIeFlitExtension*>(&ext);
        this->flit_id = flit_ext->flit_id;
        this->is_ack = flit_ext->is_ack;
        this->is_nak = flit_ext->is_nak;
        this->payload_size = flit_ext->payload_size;
        this->is_tail = flit_ext->is_tail;
    }
};

#endif // PCIE_EXTENSIONS_H
