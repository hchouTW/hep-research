"""Protected-use mode (task P1, HC-09, K08), standard library only: core.protected.guard decides whether an entry point
runs in protected mode and refuses it when the revocation or qualification inputs cannot be established;
trusted_input checks that a protected input comes from another identity; revocation_log verifies the hash-chained
revocation log; identity computes the running plugin's code identity. Advisory: an in-process check stops an accidental
or omitted check, not a process that rewrites the code; enforcement lies with the data and egress planes."""
