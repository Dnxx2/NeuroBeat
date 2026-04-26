using System;
using System.IO;
using UnityEngine;
using System.Collections.Generic;

public static class SavWav {

    const int HEADER_SIZE = 44;

    // Guarda en cualquier ruta absoluta (como el Escritorio)
    public static bool SaveAbsolute(string filepath, AudioClip clip) {
        if (!filepath.ToLower().EndsWith(".wav")) {
            filepath += ".wav";
        }

        string directory = Path.GetDirectoryName(filepath);
        if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);

        using (var fileStream = CreateEmpty(filepath)) {
            ConvertAndWrite(fileStream, clip);
            WriteHeader(fileStream, clip);
            fileStream.Flush(); 
        }

        Debug.Log("WAV guardado físicamente en: " + filepath);
        return true;
    }

    static FileStream CreateEmpty(string filepath) {
        var fileStream = new FileStream(filepath, FileMode.Create);
        byte emptyByte = new byte();
        for (int i = 0; i < HEADER_SIZE; i++) fileStream.WriteByte(emptyByte);
        return fileStream;
    }

    static void ConvertAndWrite(FileStream fileStream, AudioClip clip) {
        // Extraemos samples * canales para no perder el Stereo
        var samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0);

        Int16[] intData = new Int16[samples.Length];
        Byte[] bytesData = new Byte[samples.Length * 2];
        const int rescaleFactor = 32767;

        for (int i = 0; i < samples.Length; i++) {
            // SEGURIDAD: Evita que el audio "explote" si supera 1.0
            float sampleSeguro = Mathf.Clamp(samples[i], -1f, 1f);
            
            intData[i] = (short)(sampleSeguro * rescaleFactor);
            Byte[] byteArr = BitConverter.GetBytes(intData[i]);
            byteArr.CopyTo(bytesData, i * 2);
        }

        fileStream.Write(bytesData, 0, bytesData.Length);
    }

    static void WriteHeader(FileStream fileStream, AudioClip clip) {
        var hz = clip.frequency;
        var channels = clip.channels;
        var samples = clip.samples;

        fileStream.Seek(0, SeekOrigin.Begin);

        fileStream.Write(System.Text.Encoding.UTF8.GetBytes("RIFF"), 0, 4);
        fileStream.Write(BitConverter.GetBytes(fileStream.Length - 8), 0, 4);
        fileStream.Write(System.Text.Encoding.UTF8.GetBytes("WAVE"), 0, 4);
        fileStream.Write(System.Text.Encoding.UTF8.GetBytes("fmt "), 0, 4);
        fileStream.Write(BitConverter.GetBytes(16), 0, 4);
        fileStream.Write(BitConverter.GetBytes((UInt16)1), 0, 2);
        fileStream.Write(BitConverter.GetBytes((UInt16)channels), 0, 2);
        fileStream.Write(BitConverter.GetBytes((UInt32)hz), 0, 4);
        fileStream.Write(BitConverter.GetBytes((UInt32)(hz * channels * 2)), 0, 4);
        fileStream.Write(BitConverter.GetBytes((UInt16)(channels * 2)), 0, 2);
        fileStream.Write(BitConverter.GetBytes((UInt16)16), 0, 2);
        fileStream.Write(System.Text.Encoding.UTF8.GetBytes("data"), 0, 4);
        fileStream.Write(BitConverter.GetBytes(samples * channels * 2), 0, 4);
    }
}