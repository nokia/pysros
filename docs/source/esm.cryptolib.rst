The :mod:`pysros.esm.cryptolib` module provides a set of classes and functions that can be used 
to encrypt and decrypt data.

.. note:: This module is available when executing on SR OS only. On a remote
          machine, the :mod:`pysros.esm.cryptolib` module is not supported.

This module is only available when a Python application is triggered by the Enhanced Subscriber 
Management (ESM) application on SR OS.
   
The general principle is to create cipher object of the type of :class:`pysros.esm.cryptolib.AES` 
with which you want to encrypt and decrypt data.

This object is created with all required parameters once, after which it can be used multiple times
to either encrypt or decrypt pieces of data.

.. note:: The cipher object contains all information needed to encrypt and decrypt data.
          Depending on the block-mode used, this also contains the intermediate state needed to
          chain multiple blocks of data. For these block-modes, an object can only be used for encryption
          or decryption, but not both at the same time.

          :data:`MODE_ECB` is an exception because it does not use chaining, hence this object *can* be used
          for both encryption and decryption at the same time.

.. Reviewed by PLM 20250127

**Cryptography**

.. class:: pysros.esm.cryptolib.AES(key, mode, *, padding=None, iv=None)

   Create a new AES cipher object.
   This object can then be used to encrypt and decrypt data.

   :param key: The secret key to use. It must be 16, 24, or 32 bytes long (respectively for *AES-128*, 
               *AES-192* and *AES-256*).
   :type key: bytes

   :param mode: The chaining mode.
   :type mode: One of the constants :data:`MODE_ECB` or :data:`MODE_CBC`.

   :param padding: The padding algorithm to be automatically applied.
                   When provided, the cleartext will be automatically padded/unpadded.
                   The value of this attribute is the *style* of padding to use.
                   This method can only be used if the complete data to be encrypted or decrypted is passed in as a whole.
                   In case the data is encrypted in multiple invocations of :meth:`pysros.esm.cryptolib.AES.encrypt` 
                   and  :meth:`pysros.esm.cryptolib.AES.decrypt`, manual (un)padding needs to be applied on the last block.
                   See the documentation for :func:`pad` for the supported values.
   :type padding: string, optional

   :param iv: The initial vector.  For mode :data:`MODE_ECB` this argument is not valid.
              For mode :data:`MODE_CBC` it must be 16 bytes long.
              If not provided (but required), a random bytestring is generated.
              Its value must then be read via the :attr:`iv` attribute.
   :type iv: bytes, optional

   .. Reviewed by PLM 20250127

   .. method:: encrypt(plaintext, /, *, output=None)

      Encrypt plaintext.
        
      The function either returns the encrypted data or places it in a preallocated buffer
      passed in via the ``output`` parameter.

      :param plaintext: The plaintext that needs to be encrypted. Should be a multiple of 
                        the configured ``block_size``, unless automatic padding is configured.

      :type plaintext: bytes

      :param output: Preallocated buffer into which the encrypted data is written.
                     The input must be of the correct size (i.e. the same length as the 
                     plaintext input).  It cannot be used when the object is configured to 
                     automatically apply padding, as the size might increase due to an 
                     extra padding-block.
      :type output: bytearray
        
      :returns: The ciphertext or ``None`` when an ``output`` buffer was provided.
      :rtype: bytes

      .. code-block:: python3
         :caption: Example: Encrypting
         :emphasize-lines: 5
        
         from pysros.esm.cryptolib import AES, MODE_ECB

         key = b'0123456789abcdef'
         aes = AES(key, MODE_ECB, padding='pkcs7')
         aes.encrypt(b'My super-secret message')
         # b'\xd8V\x01\x08\xb9f\xad\xbe\xa1\xbe\x8c\xe4I0E\xc7J\xf1W\xf9\xa0\xf8\x18Nu\xb5\xbd\xe9L_E\xa7'

   .. Reviewed by PLM 20250127

   .. method:: decrypt(ciphertext, /, *, output=None)

      Decrypt ciphertext.

      The function either returns the plaintext data or places it in a preallocated buffer
      passed in via the ``output`` parameter.

      :param ciphertext: The ciphertext that needs to be decrypted. Should be a multiple of 
                         the configured ``block_size``, unless automatic padding is configured.
      :type ciphertext: bytes

      :param output: Preallocated buffer into which the decrypted plaintext is written.
                     Must be of the correct size (i.e. the same length as the ciphertext input).
                     It cannot be used when the object is configured to automatically apply padding,
                     as the size might decrease due to stripped padding.
      :type output: bytearray
        
      :returns: The plaintext or ``None`` when an ``output`` buffer was provided.
      :rtype: bytes

      .. code-block:: python3
         :caption: Example: Decrypting
         :emphasize-lines: 5
            
         from pysros.esm.cryptolib import AES, MODE_ECB

         key = b'0123456789abcdef'
         aes = AES(key, MODE_ECB, padding='pkcs7')
         aes.decrypt(b'\xd8V\x01\x08\xb9f\xad\xbe\xa1\xbe\x8c\xe4I0E\xc7J\xf1W\xf9\xa0\xf8\x18Nu\xb5\xbd\xe9L_E\xa7')
         #b'My super-secret message'


.. note:: All places where parameters of type `bytes` are expected, objects of type bytearray or str can also be provided.

.. Reviewed by PLM 20250127

**Mode constants**

.. py:data:: MODE_ECB

    Electronic Code Book mode.

.. py:data:: MODE_CBC
    
    Cipher-Block Chaining mode

.. Reviewed by PLM 20250127

**Utilities**

.. function:: pysros.esm.cryptolib.pad(data, block_size, /, style='pkcs7')

   Apply standard padding.

   :param data: The data that needs to be padded.
   :type data: bytes
   :param block_size: The block size to use. The output is a multiple of ``block_size``.
   :type block_size: int
   :param style: Padding algorithm. It can be ``pkcs7``, ``iso7816`` or ``x923``.  Default: ``pkcs7``.
   :tyoe style: str, optional
   :return: The original data with appropriate padding added to the end.
            If the length of ``data`` is already a multiple of ``block_size``, a whole extra block will be added.
   :rtype: bytes

.. Reviewed by PLM 20250127

.. function:: pysros.esm.cryptolib.unpad(data, block_size, /, style='pkcs7')

   Remove standard padding.

   :param data: The data that needs to be stripped of padding.
   :type data: bytes
   :param block_size: The block size to use. The input must be a multiple of ``block_size``.
   :type block_size: int
   :param style: Padding algorithm. It can be ``pkcs7``, ``iso7816`` or ``x923``.  Default: ``pkcs7``.
   :type style: str, optional
   :return: The data without the padding bytes.
   :rtype: bytes
   :raises ValueError: If the padding is incorrect.
    
.. Reviewed by PLM 20250127


