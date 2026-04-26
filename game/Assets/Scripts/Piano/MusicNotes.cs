using UnityEngine;

public class MusicNotes : MonoBehaviour
{
    public AudioSource Do_note;
    public AudioSource Do1_note;
    public AudioSource Re_note;
    public AudioSource Re1_note;
    public AudioSource Mi_note;
    public AudioSource Fa_note;
    public AudioSource Fa1_note;
    public AudioSource Sol_note;
    public AudioSource Sol1_note;
    public AudioSource La_note;
    public AudioSource La1_note;
    public AudioSource Si_note;

    public void PlayDo()
    {
        Do_note.PlayOneShot(Do_note.clip);
    }

    public void PlayDo1()
    {
        Do1_note.PlayOneShot(Do1_note.clip);
    }

    public void PlayRe()
    {
        Re_note.PlayOneShot(Re_note.clip);
    }

    public void PlayRe1()
    {
        Re1_note.PlayOneShot(Re1_note.clip);
    }

    public void PlayMi()
    {
        Mi_note.PlayOneShot(Mi_note.clip);
    }

    public void PlayFa()
    {
        Fa_note.PlayOneShot(Fa_note.clip);
    }

    public void PlayFa1()
    {
        Fa1_note.PlayOneShot(Fa1_note.clip);
    }

    public void PlaySol()
    {
        Sol_note.PlayOneShot(Sol_note.clip);
    }

    public void PlaySol1()
    {
        Sol1_note.PlayOneShot(Sol1_note.clip);
    }

    public void PlayLa()
    {
        La_note.PlayOneShot(La_note.clip);
    }

    public void PlayLa1()
    {
        La1_note.PlayOneShot(La1_note.clip);
    }

    public void PlaySi()
    {
        Si_note.PlayOneShot(Si_note.clip);
    }
}
