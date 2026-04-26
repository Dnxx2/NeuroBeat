using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SocialPlatforms.Impl;
using UnityEngine.UI;
public class GameManager : MonoBehaviour
{
    public AudioSource theMusic;
    public bool startPlaying;
    public Beatscroller theBS;
    public static GameManager instance;
    public int currentScore;
    public int currentMultiplier;
    public int scorePerNote = 100;
    public int scorePerGoodNote = 150;
    public int scorePerPerfectNote = 200;   
    public GameObject normalHitEffect;
    
    public Text scoreText;
    public Text multiText;
    public float totalNotes; 
    public float normalHits;
    public float perfectHits;
    public float goodHits;
    public float missedHits;

    public GameObject resultsScreen;
    public Text percentHitText,normalsText, goodsText, perfectsText, missedText,rankText,finalscoreText;


    // Awake se ejecuta incluso antes que Start. Es el lugar ideal para configurar instancias estáticas.
    void Awake()
    {
        
        instance = this;
    }

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        scoreText.text = "Score: 0";
        currentMultiplier = 1;

        totalNotes = FindObjectsOfType<NodeObject>().Length;
    }

    // Update is called once per frame
    void Update()
    {
        if (!startPlaying)
        {
            if (Input.anyKeyDown)
            {
                startPlaying = true;
                theBS.hasStarted = true;
                theMusic.Play();
            }
        }
        else
        {
            if (!theMusic.isPlaying && !resultsScreen.activeInHierarchy)
            {
                resultsScreen.SetActive(true);
                percentHitText.text = "Hit Percentage: " + Mathf.Round(((normalHits + goodHits + perfectHits) / totalNotes) * 100f) + "%";
                normalsText.text = "Normal Hits: " + normalHits;
                goodsText.text = "Good Hits: " + goodHits;
                perfectsText.text = "Perfect Hits: " + perfectHits;
                missedText.text = "Missed Hits: " + missedHits;
                finalscoreText.text = "Final Score: " + currentScore;
                float hitPercentage = (normalHits + goodHits + perfectHits) / totalNotes;
                if (hitPercentage >= 0.9f)
                {
                    rankText.text = "Rank: S";
                }
                else if (hitPercentage >= 0.8f)
                {
                    rankText.text = "Rank: A";
                }
                else if (hitPercentage >= 0.7f)
                {
                    rankText.text = "Rank: B";
                }
                else if (hitPercentage >= 0.6f)
                {
                    rankText.text = "Rank: C";
                }
                else
                {
                    rankText.text = "Rank: D";
                }
            }
        }
    }
    public void NoteHit()
    {
        Debug.Log("Hit");

        /*
        if (currentMultiplier - 1 < multiplierThresholds.Length)
        {
            multiplierTracker++;
            if (multiplierThresholds[currentMultiplier - 1] <= multiplierTracker)
            {
                multiplierTracker = 0;
                currentMultiplier++;
            }
        }deprecated
        */ 
    

        
        scoreText.text = "Score: " + currentScore;
    }

    public void NoteMiss()
    {
        Debug.Log("Miss");
        /*
        // Castigo por fallar: el multiplicador y el contador regresan a sus valores iniciales
        currentMultiplier = 1;
        multiplierTracker = 0;

        // Actualizamos el texto para que el jugador sufra viendo que perdió su combo
        multiText.text = "Multiplier: x" + currentMultiplier; deprecated*/ 
        missedHits++;
    }
    public void NormalHit()
    {
        currentScore += scorePerNote * currentMultiplier;
        
        NoteHit();
        normalHits++;
    }
    public void GoodHit()
    {
        currentScore += scorePerGoodNote * currentMultiplier;
        NoteHit();
        goodHits++;
    }
    public void PerfectHit()
    {
        currentScore += scorePerPerfectNote * currentMultiplier;
        NoteHit();
        perfectHits++;
    }
}