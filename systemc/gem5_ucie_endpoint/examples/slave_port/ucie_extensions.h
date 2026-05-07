#ifndef UCIE_EXTENSIONS_H
#define UCIE_EXTENSIONS_H

#include <tlm>
#include <cstdint>

class UCIeFlitExtension : public tlm::tlm_extension<UCIeFlitExtension> {
public:
    uint64_t flit_id;
    bool is_ack;
    bool is_nak;
    uint32_t payload_size;
    bool is_tail;

    UCIeFlitExtension()
        : flit_id(0), is_ack(false), is_nak(false), payload_size(0), is_tail(false) {}

    virtual tlm_extension_base* clone() const override {
        UCIeFlitExtension* ext = new UCIeFlitExtension();
        ext->flit_id = this->flit_id;
        ext->is_ack = this->is_ack;
        ext->is_nak = this->is_nak;
        ext->payload_size = this->payload_size;
        ext->is_tail = this->is_tail;
        return ext;
    }

    virtual void copy_from(tlm_extension_base const& ext) override {
        const UCIeFlitExtension* flit_ext = static_cast<const UCIeFlitExtension*>(&ext);
        this->flit_id = flit_ext->flit_id;
        this->is_ack = flit_ext->is_ack;
        this->is_nak = flit_ext->is_nak;
        this->payload_size = flit_ext->payload_size;
        this->is_tail = flit_ext->is_tail;
    }
};

#endif // UCIE_EXTENSIONS_H
