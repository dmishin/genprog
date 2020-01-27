#Hand-maintained map of hashes that are compatible
_hash_compatibility = {
    #remap due to logic change
    "0c98c7aa961c828e867a8ddddcc1d9b7":"2c17b56b450cb32438af36242f994487"
}

def hashes_compatible(h1, h2):
    return (h1 == h2) or (_hash_compatibility.get(h1,h1)==_hash_compatibility.get(h2,h2))
