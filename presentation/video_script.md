# Video script: Predicting HDI groups (DS203)

About **1243 words**, roughly **9:35** when spoken at a relaxed pace (about 130 words a minute). The limit is 10 minutes, so there is some room for pauses.

The final slides have no speaker notes, so read from this file (the slides are in `HDI_presentation.pdf`).

## Who says what

| Speaker | Slides | Part | Time |
|---|---|---|---|
| Vivaan | 2–5 | The question and the data | about 3:10 (411 words) |
| Shivam | 6–9 | The method | about 2:55 (385 words) |
| Tanush | 10–13 | The results and wrap-up | about 3:10 (413 words) |
| All three | 1 and 14 | Hello and goodbye | a few seconds |

## Recording checklist

- The project rules say **every member must be visible and speaking**. The simplest way is a Zoom or Google Meet call with all three cameras on, one person sharing the slides, and the call recorded.
- The label at the bottom of each slide shows who is speaking.
- Do one full practice run with a timer. If you go over 9:45, trim the longer slides (2, 4, 5 and 8) first.
- Export as **mp4**.

## Script

### Slide 1: Title
*Vivaan, Shivam, Tanush, about 15 seconds*

VIVAAN: Hi, I'm Vivaan.

SHIVAM: I'm Shivam.

TANUSH: And I'm Tanush.

VIVAAN: In this video, we'll find out whether a handful of everyday statistics about a country can tell us how developed it is.

### Slide 2: What is the HDI?
*Vivaan, about 55 seconds*

Every year the United Nations gives each country a score called the Human Development Index, or HDI. It runs from 0 to 1 and combines three things: how long people live, how much schooling they get, and how much they earn. Iceland is at the top with 0.97, and South Sudan is at the bottom with 0.39.

The catch is that the HDI depends on exactly that data, which takes time to collect and publish. So we asked: if we leave those three out and use other, more commonly collected statistics, like internet use or how many babies survive their first year, can we still tell which development group a country belongs to? And which statistics matter most?

### Slide 3: Three groups
*Vivaan, about 30 seconds*

We split the HDI scale into three groups. Below 0.55 is Low, for example Niger. From 0.55 up to 0.8 is Medium-to-High, which includes India and Brazil. And 0.8 or above is Very High, like Germany or Japan. This split is our own; the UN officially uses four groups. Notice that the groups are uneven: only 26 countries are Low, compared with 93 and 74. That will matter later.

### Slide 4: Our data
*Vivaan, about 50 seconds*

For our clues we turned to the World Bank, which publishes statistics for almost every country. We took nine numbers, nearly all from 2023, with a few gaps filled from the three years before. Three describe the economy, three describe daily life, and three describe what the economy is made of. We also added two labels: the region, and the country's main sector.

Just as important is what we left out. Life expectancy, schooling and income are the HDI's own ingredients, so using them would be like handing the model the answer key. After matching the UN and World Bank lists, we had 193 countries.

### Slide 5: What the data shows
*Vivaan, about 55 seconds*

Before building any model, we looked at the data. Each dot here is a country. On the left, infant deaths: a typical Low country loses about 46 babies in every 1,000 births, while a typical Very High country loses 4. On the right, internet use rises from about a fifth of people to more than nine in ten. Farming share and electricity also differ a lot, and these clues move together, so they mostly measure one thing: overall development.

One more finding: gaps in the data aren't random. 31% of Low countries and 27% of Medium-to-High ones are missing at least one number, compared with 12% of Very High ones. Shivam will now explain how we built our models.

### Slide 6: A fair final exam
*Shivam, about 35 seconds*

Thanks, Vivaan. The first rule of testing a model is: don't show it the exam in advance. So we shuffled the countries into three piles: 115 for training, 39 for checking along the way, and 39 locked away as a final exam. Each pile has the same mix of the three groups. Every step that learns from data, even filling in blanks, was learned from the training pile only, so nothing leaked from the exam.

### Slide 7: Filling in the blanks
*Shivam, about 50 seconds*

Speaking of blanks: most models can't work with an empty cell, so we have to fill it. Take Sudan, which has no internet figure. A simple fix is to fill in the training average, about 70%. But the typical Low country is at about 20%, so that is probably a poor guess. So we also add a small yes-or-no flag that says 'this value was missing'. We tested the median against the average, with and without the flag. The differences were small, but the flag helped a little on average, so we went with the average plus the flag. It isn't magic: our final model still got Sudan wrong.

### Slide 8: Four models
*Shivam, about 50 seconds*

Next, we compared four models, from simplest to most flexible.

The baseline ignores the data and always guesses the most common group.

Logistic regression works like a weighted scorecard: each clue adds or removes points for each group, and the group with the most points wins.

A decision tree plays twenty questions. Ours first asks: do fewer than 9 in 1,000 babies die? If not, are fewer than a third of people online? If so, do more than 37 in 1,000 babies die? Then it answers 'Low'.

And a random forest is a committee: 300 slightly different trees, each trained on a random sample of countries, vote on the answer.

### Slide 9: Picking the winner
*Shivam, about 40 seconds*

How do we pick the winner? First, cross-validation. We cut the training pile into five parts, train on four, quiz on the fifth, and rotate, so every country gets a turn in the quiz.

Second, the score itself. Plain accuracy can fool you: our baseline is right 49% of the time on the exam without finding a single Low country. So we used macro F1, which grades each group separately and then averages, so the small Low group counts as much as the big ones. Over to Tanush for the results.

### Slide 10: Results
*Tanush, about 50 seconds*

Thanks, Shivam. Here's how the models did on the 39 exam countries they had never seen. The random forest, which we picked using cross-validation, got 32 right, or 82%. Logistic regression did just as well. Both are far ahead of the baseline's 49%.

Now look at the last column. There were five Low countries in the exam. The decision tree found none of them, even though its accuracy, 79%, looks almost as good. That's exactly why we didn't rely on accuracy alone.

The forest's macro F1 also fell, from 0.92 in cross-validation to 0.73 here, mainly because it found only two of the five Low countries.

### Slide 11: Where it goes wrong
*Tanush, about 40 seconds*

This grid shows the random forest's answers. Rows are the true group, columns are the model's guess, and the diagonal is where it's right. Two things stand out. First, the forest's mistakes are all between neighbouring groups; it never mixes up a Low country with a Very High one. Second, all seven misses are within 0.04 of a dividing line. Tanzania, at 0.555, is just above the 0.55 line and was called Low. When a sharp line cuts through a smooth scale, mistakes like these are expected.

### Slide 12: Which clues mattered
*Tanush, about 50 seconds*

Which clues did the model rely on? To find out, we scrambled one clue at a time and measured how much the score dropped. The biggest drops came from infant deaths, internet use and farming share, with region almost level and electricity next. Inflation, unemployment and trade mattered little. The main-sector label only looks useful here because two exam countries were missing it; in our other tests it added nothing.

We also squeezed all the inputs into just two summary numbers, using a technique called PCA, and logistic regression did just as well, though the random forest got worse. So these clues largely measure one underlying thing.

### Slide 13: Limits and takeaway
*Tanush, about 50 seconds*

A few cautions. 193 countries is every country with an HDI, so there's no more data to collect, and with only five Low countries in the exam, each one moves the score a lot. Less developed countries have more missing data. And most importantly, this shows association, not cause: we can't say that changing one statistic would change a country's HDI. Infant deaths also overlap with life expectancy, which is part of the HDI.

To sum up: everyday statistics put a country in the right group about four times out of five. Very High countries are easy to spot, Low ones are hard, and the misses were all close to a dividing line.

### Slide 14: Thank you
*All three, about 5 seconds*

ALL: Thank you for watching!

## Numbers used, for quick checking

- 193 countries; groups 26 Low / 93 Medium-High / 74 Very High (HDI 2023, UNDP HDR 2025).
- Split 115 / 39 / 39. Final exam has 5 Low, 19 Medium-High, 15 Very High countries.
- Final exam: random forest and logistic regression 82% accuracy (32 of 39), macro F1 0.73; decision tree 79% (31 of 39), macro F1 0.57, 0 of 5 Low found; baseline 49%, macro F1 0.22.
- Random forest macro F1: 0.92 in cross-validation, 0.73 on the final exam. All 7 exam misses are within 0.04 of a cut-off.
- Median infant deaths per 1,000 births: 46 / 18 / 4. Median internet use: 20% / 69% / 92%.
- Countries missing at least one number: 31% of Low, 27% of Medium-High, 12% of Very High.
- Decision tree's first questions (converted from the standardised scale): infant deaths about 9 per 1,000, internet use about 34%, infant deaths about 37 per 1,000.
- Sudan's missing internet value is filled with the training average, 69.6%.
